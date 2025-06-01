class StackMachine:
    def __init__(self):
        self.stack = []                       # Pila principal
        self.memory = [0] * 1024              # Memoria lineal
        self.globals = {}                     # Variables globales
        self.locals_stack = []                # Stack de variables locales por función
        self.call_stack = []                  # Stack de retorno
        self.functions = {}                   # Diccionario de funciones
        self.pc = 0                           # Contador de programa
        self.program = []                     # Programa IR cargado
        self.running = False

    def load_program(self, program):
        self.program = program

    def run(self):
        self.pc = 0
        self.running = True
        while self.running and self.pc < len(self.program):
            instr = self.program[self.pc]
            opname = instr[0]
            args = instr[1:] if len(instr) > 1 else []
            method = getattr(self, f"op_{opname}", None)
            if method:
                method(*args)
            else:
                raise RuntimeError(f"Instrucción desconocida: {opname}")
            self.pc += 1

    def op_CONSTI(self, value):
        self.stack.append(('int', value))

    def op_ADDI(self):
        b_type, b = self.stack.pop()
        a_type, a = self.stack.pop()
        if a_type == b_type == 'int':
            self.stack.append(('int', a + b))
        else:
            raise TypeError("ADDI requiere dos enteros")

    def op_PRINTI(self):
        val_type, value = self.stack.pop()
        if val_type == 'int':
            print(value)
        else:
            raise TypeError("PRINTI requiere un entero")

    def op_RET(self):
        self.running = False



program = [
    ('CONSTI', 10),
    ('CONSTI', 20),
    ('ADDI',),
    ('PRINTI',),
    ('RET',),
]

vm = StackMachine()
vm.load_program(program)
vm.run()