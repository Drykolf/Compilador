import struct
from rich import print
import json,os

def load_config():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, '..', 'settings', 'config.json')
        if not os.path.exists(config_path): 
             config_path = os.path.join(os.path.dirname(__file__), '..', 'settings', 'config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: config.json not found (tried {config_path}), using default settings")
        return {"Debug": True, "GenerateOutputFile": False} 
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in config.json (at {config_path}), using default settings")
        return {"Debug": True, "GenerateOutputFile": False}
    except Exception as e:
        print(f"Warning: Error loading config.json (at {config_path}): {e}, using default settings")
        return {"Debug": True, "GenerateOutputFile": False}

CONFIG = load_config()

class StackMachine:
    def __init__(self, memory_size=1024 * 1024 * 8): # Increased memory for Mandelbrot image (e.g. 800x800x4 bytes)
        self.debug = CONFIG.get("Debug", True) 
        self.stack = []
        self.memory = bytearray(memory_size)
        self.globals = {}
        self.locals_stack = []
        self.call_stack = []
        self.functions = {}
        self.pc = 0
        self.program_instructions = []
        self.running = False
        self.current_function_name = None
        self.loop_start_stack = []
        self.if_start_stack = [] 
        self.pc_just_set_by_control_flow = False

        self.INT_SIZE = 4
        self.FLOAT_SIZE = 4
        
    def _log_debug(self, message, flush=False): 
        if self.debug:
            print(message, flush=flush)

    def _get_typed_value_from_stack(self):
        if not self.stack:
            call_stack_summary = [(item.get('previous_function_name', 'N/A'), item.get('return_pc', 'N/A')) for item in self.call_stack]
            active_function = self.current_function_name if self.current_function_name else "Global/Unknown"
            instr_preview = self.program_instructions[self.pc] if self.pc < len(self.program_instructions) else "N/A"
            raise RuntimeError(f"Stack underflow in function {active_function} (PC={self.pc}, Instr={instr_preview}). Call stack (caller, ret_pc): {call_stack_summary}")
        return self.stack.pop()

    def _get_value_from_stack(self, expected_type_str):
        if not self.stack:
            call_stack_summary = [(item.get('previous_function_name', 'N/A'), item.get('return_pc', 'N/A')) for item in self.call_stack]
            active_function = self.current_function_name if self.current_function_name else "Global/Unknown"
            instr_preview = self.program_instructions[self.pc] if self.pc < len(self.program_instructions) else "N/A"
            raise RuntimeError(f"Stack underflow in function {active_function} (PC={self.pc}, Instr={instr_preview}): expected {expected_type_str}. Call stack: {call_stack_summary}")
        
        stype, value = self.stack[-1] # Peek first for logging
        self._log_debug(f"--- _get_value_from_stack: Expecting '{expected_type_str}'. Stack top: ({stype}, {value}). PC={self.pc} in {self.current_function_name}", flush=True)
        
        stype_pop, value_pop = self.stack.pop() # Actual pop

        if stype_pop != expected_type_str:
            raise TypeError(f"Type mismatch on stack (PC={self.pc} in {self.current_function_name}): expected {expected_type_str}, got {stype_pop} (value: {value_pop})")

        if expected_type_str == 'int' and not isinstance(value_pop, int):
            try: value_pop = int(value_pop)
            except ValueError: raise TypeError(f"Value {value_pop} from stack cannot be converted to int.")
        elif expected_type_str == 'float' and not isinstance(value_pop, float):
            try: value_pop = float(value_pop)
            except ValueError: raise TypeError(f"Value {value_pop} from stack cannot be converted to float.")
        return value_pop

    def _push_value_to_stack(self, value, type_char):
        stack_type = 'unknown'
        original_stack_id = id(self.stack)
        # self._log_debug(f"--- _push_value_to_stack: Value={value}, TypeChar='{type_char}'. Stack BEFORE (id={original_stack_id}): {list(self.stack)}", flush=True)

        if type_char == 'I':
            stack_type = 'int'
            if not isinstance(value, int):
                try: value = int(value)
                except (ValueError, TypeError): raise TypeError(f"Cannot convert value {value} to int for IR type 'I'.")
        elif type_char == 'F':
            stack_type = 'float'
            if not isinstance(value, float):
                try: value = float(value)
                except (ValueError, TypeError): raise TypeError(f"Cannot convert value {value} to float for IR type 'F'.")
        else:
            raise TypeError(f"Unknown IR type character for push: {type_char}")
        
        self.stack.append((stack_type, value))
        # self._log_debug(f"--- _push_value_to_stack: Stack AFTER (id={id(self.stack)}, should be same as {original_stack_id}): {list(self.stack)}", flush=True)
        if id(self.stack) != original_stack_id:
            self._log_debug(f"[bold red][CRITICAL_ERROR][/bold red] self.stack object ID changed during _push_value_to_stack!", flush=True)


    def load_module(self, ir_module):
        self.functions = {}
        for name, func_def in ir_module.functions.items():
            self.functions[name] = {
                'params': func_def.parmnames, 
                'param_types': func_def.parmtypes, 
                'code': func_def.code,
                'locals_spec': func_def.locals,
                'return_type': func_def.return_type,
                'is_imported': func_def.imported
            }
        self.globals = { name: (None, ir_module.globals[name].type) for name in ir_module.globals }
        if 'main' not in self.functions:
            raise RuntimeError("No 'main' function found in IR module to start execution.")

    def run(self):
        if not self.functions or 'main' not in self.functions:
            print("Error: Program not loaded or 'main' function is missing.")
            return

        self.op_CALL('main', is_initial_call=True)
        
        if self.debug and self.program_instructions: # Check if program_instructions is populated
            self._log_debug("--- Initial Program Instructions (main) ---")
            for idx, instr_tuple in enumerate(self.program_instructions[:min(60, len(self.program_instructions))]): 
                self._log_debug(f"PC {idx:03d}: {instr_tuple}")
            self._log_debug("--------------------------------------------")

        self.running = True
        instruction_count = 0
        max_instructions = 10 * 1000 * 1000 

        while self.running:
            if instruction_count > max_instructions:
                print(f"[bold red]MAX INSTRUCTION COUNT ({max_instructions}) REACHED.[/bold red]")
                self.running = False
                break
            instruction_count += 1

            if self.pc >= len(self.program_instructions):
                if not self.call_stack: 
                    self.running = False
                    break
                else: 
                    self._log_debug(f"[bold yellow][DEBUG_WARN][/bold yellow] End of instructions for {self.current_function_name}. Implicit RET.")
                    current_func_ret_type = self.functions[self.current_function_name]['return_type']
                    if current_func_ret_type == 'F' and (not self.stack or self.stack[-1][0] != 'float'):
                        self.stack.append(('float', 0.0))
                    elif current_func_ret_type == 'I' and (not self.stack or self.stack[-1][0] != 'int'):
                         self.stack.append(('int', 0))
                    self.op_RET()
                    if not self.running: break 
                    continue

            instr = self.program_instructions[self.pc]
            opname = instr[0]
            args = instr[1:] if len(instr) > 1 else []

            if self.debug and opname in {"IF", "ELSE", "ENDIF", "CALL", "RET", "LOOP", "ENDLOOP", "CBREAK", "ITOF", "LOCAL_GET"}: 
                self._log_debug(f"[bold yellow][DISPATCH_{opname}][/bold yellow] PC:{self.pc:03d} F:'{self.current_function_name}'. IF_S: {list(self.if_start_stack)}, LOOP_S: {list(self.loop_start_stack)} StackTop: {self.stack[-3:] if len(self.stack) >=3 else list(self.stack)}", flush=True)

            self.pc_just_set_by_control_flow = False
            method_name = f"op_{opname}"
            method = getattr(self, method_name, None)

            if method:
                try:
                    method(*args)
                except Exception as e:
                    print(f"[bold red]Runtime Error during '{opname}' at PC {self.pc} in '{self.current_function_name}': {e}[/bold red]")
                    print(f"Instruction: {instr}, Stack: {self.stack}, Locals: {self.locals_stack[-1] if self.locals_stack else 'N/A'}")
                    self.running = False 
            else:
                self.running = False
                raise RuntimeError(f"Unknown instruction: {opname} in function {self.current_function_name} at PC {self.pc}")

            if self.running:
                if not self.pc_just_set_by_control_flow:
                    self.pc += 1
        
        self._log_debug(f"[bold blue][DEBUG_RUN_END] Execution finished. Total instructions: {instruction_count}[/bold blue]")
        if self.stack:
           self._log_debug(f"[bold blue][DEBUG_RUN_END] Final stack state: {self.stack}[/bold blue]")

    def op_CONSTI(self, value): self.stack.append(('int', int(value)))
    def op_CONSTF(self, value): self.stack.append(('float', float(value)))
    def op_ADDI(self): b=self._get_value_from_stack('int'); a=self._get_value_from_stack('int'); self.stack.append(('int',a+b))
    def op_SUBI(self): b=self._get_value_from_stack('int'); a=self._get_value_from_stack('int'); self.stack.append(('int',a-b))
    def op_MULI(self): b=self._get_value_from_stack('int'); a=self._get_value_from_stack('int'); self.stack.append(('int',a*b))
    def op_DIVI(self): b=self._get_value_from_stack('int'); a=self._get_value_from_stack('int'); self.stack.append(('int',int(a/b) if b!=0 else (_ for _ in ()).throw(ZeroDivisionError("Integer division by zero"))))
    def op_ADDF(self): b=self._get_value_from_stack('float'); a=self._get_value_from_stack('float'); self.stack.append(('float',a+b))
    def op_SUBF(self): b=self._get_value_from_stack('float'); a=self._get_value_from_stack('float'); self.stack.append(('float',a-b))
    def op_MULF(self): b=self._get_value_from_stack('float'); a=self._get_value_from_stack('float'); self.stack.append(('float',a*b))
    def op_DIVF(self): b=self._get_value_from_stack('float'); a=self._get_value_from_stack('float'); self.stack.append(('float',a/b if b!=0.0 else (_ for _ in ()).throw(ZeroDivisionError("Float division by zero"))))
    def _comparison_op_int(self, op): b=self._get_value_from_stack('int');a=self._get_value_from_stack('int');self.stack.append(('int',1 if op(a,b) else 0))
    def _comparison_op_float(self, op): b=self._get_value_from_stack('float');a=self._get_value_from_stack('float');self.stack.append(('int',1 if op(a,b) else 0))
    def op_LTI(self): self._comparison_op_int(lambda a,b: a<b)
    def op_LEI(self): self._comparison_op_int(lambda a,b: a<=b)
    def op_GTI(self): self._comparison_op_int(lambda a,b: a>b)
    def op_GEI(self): self._comparison_op_int(lambda a,b: a>=b)
    def op_EQI(self): self._comparison_op_int(lambda a,b: a==b)
    def op_NEI(self): self._comparison_op_int(lambda a,b: a!=b)
    def op_LTF(self): self._comparison_op_float(lambda a,b: a<b)
    def op_LEF(self): self._comparison_op_float(lambda a,b: a<=b)
    def op_GTF(self): self._comparison_op_float(lambda a,b: a>b)
    def op_GEF(self): self._comparison_op_float(lambda a,b: a>=b)
    def op_EQF(self): self._comparison_op_float(lambda a,b: a==b)
    def op_NEF(self): self._comparison_op_float(lambda a,b: a!=b)
    def op_ANDI(self): b=self._get_value_from_stack('int');a=self._get_value_from_stack('int');self.stack.append(('int',a&b))
    def op_ORI(self): b=self._get_value_from_stack('int');a=self._get_value_from_stack('int');self.stack.append(('int',a|b))
    
    def op_ITOF(self): 
        self._log_debug(f"--- op_ITOF (PC={self.pc}) --- ENTER. Stack BEFORE pop: {list(self.stack)}", flush=True)
        val = self._get_value_from_stack('int')
        self._log_debug(f"--- op_ITOF (PC={self.pc}) --- Popped {val}. Stack AFTER pop: {list(self.stack)}", flush=True)
        self.stack.append(('float', float(val)))
        self._log_debug(f"--- op_ITOF (PC={self.pc}) --- Pushed float. Stack FINAL: {list(self.stack)}", flush=True)

    def op_FTOI(self): v=self._get_value_from_stack('float'); self.stack.append(('int',int(v)))
    def op_PEEKI(self): addr=self._get_value_from_stack('int'); self.stack.append(('int',struct.unpack('<i',self.memory[addr:addr+self.INT_SIZE])[0]))
    def op_POKEI(self): v=self._get_value_from_stack('int');addr=self._get_value_from_stack('int');self.memory[addr:addr+self.INT_SIZE]=struct.pack('<i',v)
    def op_PEEKF(self): addr=self._get_value_from_stack('int'); self.stack.append(('float',struct.unpack('<f',self.memory[addr:addr+self.FLOAT_SIZE])[0]))
    def op_POKEF(self): v=self._get_value_from_stack('float');addr=self._get_value_from_stack('int');self.memory[addr:addr+self.FLOAT_SIZE]=struct.pack('<f',v)
    def op_PEEKB(self): addr=self._get_value_from_stack('int'); self.stack.append(('int',self.memory[addr]))
    def op_POKEB(self): v=self._get_value_from_stack('int');addr=self._get_value_from_stack('int');self.memory[addr]=v
    def op_GROW(self): sz=self._get_value_from_stack('int');old=len(self.memory);self.memory.extend(bytearray(sz));self.stack.append(('int',old))
    
    def op_LOCAL_GET(self, name):
        self._log_debug(f"--- op_LOCAL_GET (PC={self.pc}) --- Name='{name}'. Stack BEFORE: {list(self.stack)}", flush=True)
        if not self.locals_stack:
            raise RuntimeError("No local scope (locals_stack is empty).")
        current_locals = self.locals_stack[-1]
        if name not in current_locals:
            raise NameError(f"Local variable '{name}' not found in function {self.current_function_name}. Available locals: {current_locals.keys()}")
        value, var_type_char = current_locals[name]
        self._log_debug(f"--- op_LOCAL_GET (PC={self.pc}) --- Retrieved ({value}, '{var_type_char}') for '{name}'. Calling _push_value_to_stack.", flush=True)
        self._push_value_to_stack(value, var_type_char)
        self._log_debug(f"--- op_LOCAL_GET (PC={self.pc}) --- Name='{name}'. Stack AFTER push: {list(self.stack)}", flush=True)

    def op_LOCAL_SET(self, name): st,v=self._get_typed_value_from_stack(); t='I' if st=='int' else 'F'; self.locals_stack[-1][name]=(v,t)
    def op_GLOBAL_GET(self, name): val,t = self.globals[name]; self._push_value_to_stack(val,t)
    def op_GLOBAL_SET(self, name): st,v=self._get_typed_value_from_stack(); _,ot=self.globals[name];nt='I' if st=='int' else 'F';assert ot==nt;self.globals[name]=(v,ot)

    def op_CALL(self, func_name, is_initial_call=False):
        # Log is now done by the run loop's DISPATCH_CALL
        if func_name not in self.functions: raise NameError(f"Function '{func_name}' not defined.")
        func_info = self.functions[func_name]
        
        if func_info['is_imported']:
            self._log_debug(f"[bold yellow][DEBUG_WARN][/bold yellow] CALL to imported '{func_name}'. Args on stack: {len(self.stack)}. Expected params: {len(func_info['params'])}. Returning default.", flush=True)
            for i in range(len(func_info['params'])):
                if not self.stack:
                    self._log_debug(f"[bold red][DEBUG_ERROR][/bold red] Stack underflow trying to pop arg {i} for imported func {func_name}", flush=True)
                    break 
                self._get_typed_value_from_stack() 
            self.stack.append(('float' if func_info['return_type'] == 'F' else 'int', 0)) 
            return

        new_locals = {}
        num_params = len(func_info['params'])
        
        if len(self.stack) < num_params:
            raise RuntimeError(f"Stack underflow: Not enough arguments on stack for function {func_name}. Expected {num_params}, got {len(self.stack)}. Stack: {list(self.stack)}")

        args_from_stack = [self._get_typed_value_from_stack() for _ in range(num_params)]
        args_from_stack.reverse()

        expected_param_types = func_info.get('param_types', [])
        if len(expected_param_types) == num_params:
            for i in range(num_params):
                arg_stype, _ = args_from_stack[i]
                expected_ir_type = expected_param_types[i]
                if (expected_ir_type == 'I' and arg_stype != 'int') or \
                   (expected_ir_type == 'F' and arg_stype != 'float'):
                    raise TypeError(f"Type mismatch for param {i} ('{func_info['params'][i]}') of {func_name}: expected IR type {expected_ir_type}, got stack type {arg_stype}")
        
        for i,p_name in enumerate(func_info['params']): 
            val_stype, val = args_from_stack[i]
            param_ir_type = expected_param_types[i] if i < len(expected_param_types) else ('I' if val_stype == 'int' else 'F')
            new_locals[p_name]=(val, param_ir_type)

        for l_name,l_type in func_info['locals_spec'].items():
            if l_name not in new_locals: new_locals[l_name]=(0.0 if l_type=='F' else 0, l_type)
        
        if not is_initial_call:
            self.call_stack.append({'return_pc':self.pc+1,'locals_frame':self.locals_stack[-1] if self.locals_stack else {},
                                    'previous_function_name':self.current_function_name,'previous_instructions':self.program_instructions})
        self.locals_stack.append(new_locals); self.program_instructions=func_info['code']; self.pc=0
        self.current_function_name=func_name; self.pc_just_set_by_control_flow=True

    def op_RET(self):
        # Log is now done by the run loop's DISPATCH_RET
        if not self.call_stack: self.running=False; self.pc_just_set_by_control_flow=True; return
        prev_frame=self.call_stack.pop(); self.pc=prev_frame['return_pc']; self.locals_stack.pop()
        self.current_function_name=prev_frame['previous_function_name']; self.program_instructions=prev_frame['previous_instructions']
        self.pc_just_set_by_control_flow=True

    def _find_jump_target(self, pc_of_initiating_op, target_op_primary, target_op_secondary=None, open_op_context=None, close_op_context=None):
        pc_scan = pc_of_initiating_op + 1
        nest_level = 0
        self._log_debug(f"[bold cyan][JUMP_FINDER][/bold cyan] START: PC_init={pc_of_initiating_op}, Find='{target_op_primary}' (Alt='{target_op_secondary}'), Context='{open_op_context}/{close_op_context}'", flush=True)
        while pc_scan < len(self.program_instructions):
            opname_scan = self.program_instructions[pc_scan][0]
            if nest_level == 0:
                if opname_scan == target_op_primary:
                    self._log_debug(f"[bold cyan][JUMP_FINDER][/bold cyan]   FOUND Primary '{target_op_primary}' at PC {pc_scan}", flush=True)
                    return pc_scan
                if target_op_secondary and opname_scan == target_op_secondary:
                    self._log_debug(f"[bold cyan][JUMP_FINDER][/bold cyan]   FOUND Secondary '{target_op_secondary}' at PC {pc_scan}", flush=True)
                    return pc_scan
            if open_op_context and opname_scan == open_op_context: nest_level += 1
            elif close_op_context and opname_scan == close_op_context: nest_level -= 1
            pc_scan += 1
        error_msg = f"Mismatched control flow: Could not find '{target_op_primary}' or '{target_op_secondary}' for op at PC {pc_of_initiating_op}."
        self._log_debug(f"[bold red][JUMP_FINDER_ERROR][/bold red] {error_msg}", flush=True) 
        raise RuntimeError(error_msg)

    def op_IF(self):
        pc_if = self.pc
        # self._log_debug(f"[bold magenta][OP_IF_PRE_APPEND][/bold magenta] PC={pc_if}. ID of self.if_start_stack: {id(self.if_start_stack)}. Content: {list(self.if_start_stack)}", flush=True)
        if self.if_start_stack is None: self.if_start_stack = []
        self.if_start_stack.append(pc_if) 
        # self._log_debug(f"[bold magenta][OP_IF_POST_APPEND_PRE_GET_COND][/bold magenta] PC={pc_if}. IF_S after append: {list(self.if_start_stack)}. ID: {id(self.if_start_stack)}", flush=True)
        condition = self._get_value_from_stack('int')
        self._log_debug(f"--- op_IF (PC={pc_if}) --- Cond={condition}, IF_S after append & get_cond: {list(self.if_start_stack)}", flush=True)

        if condition == 0: 
            self._log_debug(f"--- op_IF (PC={pc_if}) --- Cond=0 ENTER. IF_S: {list(self.if_start_stack)}", flush=True)
            try:
                jump_target_pc = self._find_jump_target(pc_if, 'ELSE', 'ENDIF', 'IF', 'ENDIF') 
                self._log_debug(f"--- op_IF (PC={pc_if}) --- Cond=0 POST_FIND. Target={jump_target_pc}. IF_S: {list(self.if_start_stack)}", flush=True)
                self.pc = jump_target_pc
                self.pc_just_set_by_control_flow = True
                self._log_debug(f"--- op_IF (PC={pc_if}) --- Cond=0 EXIT (SUCCESS). NewPC={self.pc}. IF_S: {list(self.if_start_stack)}", flush=True)
            except RuntimeError as e:
                self._log_debug(f"[bold red][OP_IF_EXCEPT][/bold red] PC={pc_if} Exception in _find_jump_target. IF_S before pop: {list(self.if_start_stack)}", flush=True)
                if self.if_start_stack and self.if_start_stack[-1] == pc_if: self.if_start_stack.pop() 
                self._log_debug(f"[bold red][OP_IF_EXCEPT][/bold red] PC={pc_if} IF_S after pop: {list(self.if_start_stack)}", flush=True)
                raise
        else: 
            self._log_debug(f"--- op_IF (PC={pc_if}) --- Cond=1 TRUE_EXIT. IF_S: {list(self.if_start_stack)}", flush=True)

    def op_ELSE(self):
        pc_else = self.pc
        self._log_debug(f"--- op_ELSE (PC={pc_else}) --- ENTER. IF_S: {list(self.if_start_stack)}", flush=True)
        if not self.if_start_stack: 
            call_stack_summary = [(item.get('previous_function_name', 'N/A'), item.get('return_pc', 'N/A')) for item in self.call_stack]
            self._log_debug(f"[bold red][OP_ELSE_ERROR_DETAIL][/bold red] Call Stack: {call_stack_summary}", flush=True)
            raise RuntimeError(f"ELSE at PC {pc_else} without matching IF on if_start_stack. Current IF_S: {list(self.if_start_stack)}")
        pc_of_if = self.if_start_stack[-1] 
        try:
            jump_target_pc = self._find_jump_target(pc_of_if, 'ENDIF', None, 'IF', 'ENDIF')
            self.pc = jump_target_pc
            self.pc_just_set_by_control_flow = True
        except RuntimeError as e: raise

    def op_ENDIF(self):
        pc_endif = self.pc
        self._log_debug(f"--- op_ENDIF (PC={pc_endif}) --- ENTER. IF_S before pop: {list(self.if_start_stack)}", flush=True)
        if not self.if_start_stack:
            self._log_debug(f"[bold yellow][DEBUG_WARN][/bold yellow] ENDIF at PC={pc_endif} encountered with empty if_start_stack.", flush=True)
        else:
            self.if_start_stack.pop()
        self._log_debug(f"--- op_ENDIF (PC={pc_endif}) --- EXIT. IF_S after pop: {list(self.if_start_stack)}", flush=True)
        
    def op_LOOP(self): self.loop_start_stack.append(self.pc)
    def op_ENDLOOP(self):
        if not self.loop_start_stack: raise RuntimeError("ENDLOOP without matching LOOP.")
        self.pc = self.loop_start_stack[-1]; self.pc_just_set_by_control_flow = True
    def op_CBREAK(self):
        condition = self._get_value_from_stack('int')
        if condition != 0: 
            if not self.loop_start_stack: raise RuntimeError(f"CBREAK at PC {self.pc} outside loop.")
            current_loop_start_pc = self.loop_start_stack[-1] 
            try:
                endloop_pc = self._find_jump_target(current_loop_start_pc, 'ENDLOOP', None, 'LOOP', 'ENDLOOP')
                self.loop_start_stack.pop() # Pop only if break is successful and target found
                self.pc = endloop_pc + 1 
                self.pc_just_set_by_control_flow = True
            except RuntimeError as e: raise 
    def op_CONTINUE(self):
        if not self.loop_start_stack: raise RuntimeError("CONTINUE outside loop.")
        self.pc = self.loop_start_stack[-1]; self.pc_just_set_by_control_flow = True

    def op_PRINTI(self): print(f"[bold green][PRINT][/bold green] OUTPUT: {self._get_value_from_stack('int')}") 
    def op_PRINTF(self): print(f"[bold green][PRINT][/bold green] OUTPUT: {self._get_value_from_stack('float')}")
    def op_PRINTB(self): v=self._get_value_from_stack('int'); print(f"[bold green][PRINT][/bold green] OUTPUT_CHAR: {chr(v)}", end='')
