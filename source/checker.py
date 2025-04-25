# check.py
'''
Este archivo contendrá la parte de verificación/validación de tipos
del compilador.  Hay varios aspectos que deben gestionarse para
que esto funcione. Primero, debe tener una noción de "tipo" en su compilador.
Segundo, debe administrar los entornos y el alcance para manejar los
nombres de las definiciones (variables, funciones, etc.).

Una clave para esta parte del proyecto es realizar pruebas adecuadas.
A medida que agregue código, piense en cómo podría probarlo.
'''
from rich    import print
from typing  import Union
from functools import singledispatchmethod
from source.model   import *
from source.symtab  import Symtab
from source.typesys import typenames, check_binop, check_unaryop


class Checker():
	@classmethod
	def check(cls, n:Node):
		'''
		1. Crear una nueva tabla de simbolos
		2. Visitar todas las declaraciones
		'''
		try:
			check = cls()
			env = Symtab("")
			n.accept(check, env)
			print("El programa es semánticamente correcto.")
			return env 
		except Exception as e:
			print(f"Error semántico: {e}")
			raise e

	@singledispatchmethod
	def visit(self, n, env):
		raise TypeError(f"Tipo de nodo inesperado: {type(n).__name__}")
	
	@visit.register
	def _(self, n: Program, env:Symtab):
		'''
		1. recorrer la lista de elementos
		'''
		print(f"Visitando nodo Program con {len(n.stmts)} declaraciones")
		for stmt in n.stmts:
			stmt.accept(self, env)

	# Statements

	@visit.register
	def _(self, n:Assignment, env:Symtab):
		'''
		1. Validar n.loc
		2. Visitar n.expr
		3. Verificar si son tipos compatibles
		'''
		if isinstance(n.location, MemoryLocation):
			# MemoryLocation is a special case, we need to check the address
			address_type = n.location.accept(self, env)
			type2 = n.expression.accept(self, env)
			return address_type
		loc = env.get(n.location.name)
		if not loc:
			raise NameError(f"La variable '{n.location.name}' no está definida.")
		if isinstance(loc, Variable):	
			if loc.is_const:
				raise TypeError(f"La variable '{n.location.name}' es de solo lectura.")

		type1 = loc.type
		type2 = n.expression.accept(self, env)
		expr_type = check_binop('=', type1, type2)
		if expr_type is None:
			raise TypeError(f"Incompatibilidad de tipos en la asignación ({n}): '{type1}' = '{type2}'")
		return expr_type

	@visit.register
	def _(self, n:Print, env:Symtab):
		'''
		1. visitar n.expr
		2. validar el tipo de n.expr
		'''
		expr_type = n.expr.accept(self, env)
		if expr_type not in typenames:
			raise TypeError(f"Tipo inválido para la declaración print: {expr_type}")

	@visit.register
	def _(self, n:If, env:Symtab):
		'''
		1. Visitar n.test (validar tipos)
		2. Crear una nueva TS para n.then y visitar Statement por n.then
		3. Si existe opcion n.else_, crear una nueva TS y visitar
		'''
		# Validate the condition type
		condition_type = n.condition.accept(self, env)
		if condition_type != 'bool':
			raise TypeError(f"La condición en la declaración if debe ser de tipo 'bool', se obtuvo '{condition_type}'")
		# Create a new symbol table for the 'then' block and visit it
		then_env = Symtab("if_then", env, n)
		for stmt in n.if_statements:
			stmt.accept(self, then_env)
		# If there is an 'else' block, create a new symbol table and visit it
		if n.else_statements:
			else_env = Symtab("if_else", env, n)
			for stmt in n.else_statements:
				stmt.accept(self, else_env)
			
	@visit.register
	def _(self, n:While, env:Symtab):
		'''
		1. Visitar n.test (validar tipos)
		2. visitar n.body
		'''
		# Validate the condition type
		condition_type = n.condition.accept(self, env)
		if condition_type != 'bool':
			raise TypeError(f"La condición en la declaración while debe ser de tipo 'bool', se obtuvo '{condition_type}'")

		# Create a new symbol table for the 'while' body and visit it
		body_env = Symtab("while_body", env, n)
		for stmt in n.statements:
			stmt.accept(self, body_env)
		
	@visit.register
	def _(self, n:Union[Break, Continue], env:Symtab):
		'''
		1. Verificar que esta dentro de un ciclo while
		'''
		current_env = env
		while current_env:
			if current_env.name.startswith("while_body"):
				return  # Valid usage of Break or Continue
			current_env = current_env.parent
		raise SyntaxError(f"La declaración '{type(n).__name__.lower()}' debe estar dentro de un ciclo 'while'.")
			
	@visit.register
	def _(self, n:Return, env:Symtab):
		'''
		1. Si se ha definido n.expr, validar que sea del mismo tipo de la función
		'''
		# Find the function scope
		current_env = env
		while current_env and not isinstance(current_env.owner, Function):
			current_env = current_env.parent
		if not current_env or not isinstance(current_env.owner, Function):
			raise SyntaxError("La declaración 'return' debe estar dentro de una función.")
		func = current_env.owner
		# If the return expression exists, validate its type
		if n.expr:
			return_type = n.expr.accept(self, env)
			if return_type != func.func_type:
				raise TypeError(f"Incompatibilidad de tipos en 'return': se esperaba '{func.func_type}', se obtuvo '{return_type}'.")
		env.add("return", n)  # Add the return statement to the function's return list

	# Declarations
	@visit.register
	def _(self, n:Variable, env:Symtab):
		'''
		1. Agregar n.name a la TS actual
		'''
		if env.get(n.name):
			raise NameError(f"La variable '{n.name}' ya está definida.")
		if n.value:
			value_type = n.value.accept(self, env)
			if n.type and n.type != value_type:
				raise TypeError(f"Incompatibilidad de tipos para la variable '{n.name}': se esperaba {n.type}, se obtuvo {value_type}")
			n.type = value_type
		env.add(n.name, n)
		
	@visit.register
	def _(self, n:Function, env:Symtab):
		'''
		1. Guardar la función en la TS actual
		2. Crear una nueva TS para la función
		3. Agregar todos los n.params dentro de la TS
		4. Visitar n.stmts
		5. Verificar que haya un return en cada camino posible
		'''
		if env.get(n.name):
			raise NameError(f"Function '{n.name}' is already defined.")
		# Ensure the function is not defined inside another function
		if env.owner != None:
			raise SyntaxError(f"La función '{n.name}' no puede definirse dentro de otra función.")
		env.add(n.name, n)
		func_env = Symtab(n.name, env, n)
		for param in n.params:
			param.accept(self, func_env)
		for stmt in n.statements:
			stmt.accept(self, func_env)
		# Check if the function has a return statement in all possible paths
		if n.func_type and not self.has_return_in_all_paths(n.statements) and not n.imported:
			raise SyntaxError(f"La función '{n.name}' debe tener una declaración 'return' en todos los caminos posibles o ser de tipo 'void'.")

	def has_return_in_all_paths(self, statements):
		'''
		Verifica si hay una declaración de retorno en todos los caminos posibles.
		'''
		for stmt in statements:
			if isinstance(stmt, Return):
				return True
			elif isinstance(stmt, If):
				then_has_return = self.has_return_in_all_paths(stmt.if_statements)
				else_has_return = self.has_return_in_all_paths(stmt.else_statements) if stmt.else_statements else False
				if then_has_return and else_has_return:
					return True
			elif isinstance(stmt, While):
				# Loops may not always guarantee a return, so skip them
				continue
		return False

	@visit.register
	def _(self, n:Parameter, env:Symtab):
		'''
		1. Guardar el parametro (name, type) en TS
		'''
		if env.get(n.name):
			raise NameError(f"El parámetro '{n.name}' ya está definido en este ámbito.")
		env.add(n.name, n)
		
	# Expressions

	@visit.register
	def _(self, n:Literal, env:Symtab):
		'''
		1. Retornar el tipo de la literal
		'''
		pass

	@visit.register
	def _(self, n:BinOp, env:Symtab):
		'''
		1. visitar n.left y luego n.right
		2. Verificar compatibilidad de tipos
		'''
		type1 = n.left.accept(self, env)
		type2 = n.right.accept(self, env)
		expr_type = check_binop(n.operator, type1, type2)
		if expr_type is None:
			raise TypeError(f"Operador '{n.operator}' no es válido para los tipos '{type1}' y '{type2}'")
		return expr_type

	@visit.register
	def _(self, n:UnaryOp, env:Symtab):
		'''
		1. visitar n.expr
		2. validar si es un operador unario valido
		'''
		type1 = n.operand.accept(self, env)
		expr_type = check_unaryop(n.operator, type1)
		if expr_type is None:
			raise TypeError(f"Operador unario '{n.operator}' no es válido para el tipo '{type1}'")
		return expr_type
	
	@visit.register
	def _(self, n:TypeCast, env:Symtab):
		'''
		1. Visitar n.expr para validar
		2. retornar el tipo del cast n.type
		'''
		expr_type = n.expr.accept(self, env)
		if expr_type not in typenames:
			raise TypeError(f"Tipo inválido para el cast: '{expr_type}'")
		if n.cast_type not in typenames:
			raise TypeError(f"Tipo de destino inválido para el cast: '{n.type}'")
		# Optionally, you can add rules to restrict certain casts
		return n.cast_type

	@visit.register
	def _(self, n:FunctionCall, env:Symtab):
		'''
		1. Validar si n.name existe
		2. visitar n.args (si estan definidos)
		3. verificar que len(n.args) == len(func.params)
		4. verificar que cada arg sea compatible con cada param de la función
		'''
		# Validate if the function exists in the symbol table
		func = env.get(n.name)
		if not func or not isinstance(func, Function):
			raise NameError(f"La función '{n.name}' no está definida.")
		# Check if the number of arguments matches the number of parameters
		if len(n.args) != len(func.params):
			raise TypeError(f"La función '{n.name}' esperaba {len(func.params)} argumentos, pero se recibieron {len(n.args)}.")
		# Validate each argument against the corresponding parameter
		for arg, param in zip(n.args, func.params):
			arg_type = arg.accept(self, env)
			if arg_type != param.type:
				raise TypeError(f"Incompatibilidad de tipos en la llamada a la función '{n.name}': se esperaba '{param.type}', se obtuvo '{arg_type}'.")
		# Return the return type of the function
		return func.func_type

	@visit.register
	def _(self, n:NamedLocation, env:Symtab):
		'''
		1. Verificar si n.name existe en TS y obtener el tipo
		2. Retornar el tipo
		'''
		symbol = env.get(n.name)
		if not symbol:
			raise NameError(f"La variable '{n.name}' no está definida.")
		return symbol.type

	@visit.register
	def _(self, n:MemoryLocation, env:Symtab):
		'''
		1. Visitar n.address (expression) para validar
		2. Retornar el tipo de datos
		'''
		address_type = n.expr.accept(self, env)
		if address_type != 'int':
			raise TypeError(f"La dirección en 'MemoryLocation' debe ser de tipo 'int', se obtuvo '{address_type}'.")
		return address_type

	@visit.register
	def _(self, n:Char, env:Symtab):
		'''
		1. Retornar el tipo de la literal Char
		'''
		return 'char'

	@visit.register
	def _(self, n:Integer, env:Symtab):
		'''
		1. Retornar el tipo de la literal Integer
		'''
		return 'int'

	@visit.register
	def _(self, n:Bool, env:Symtab):
		'''
		1. Retornar el tipo de la literal Bool
		'''
		return 'bool'

	@visit.register
	def _(self, n:Float, env:Symtab):
		'''
		1. Retornar el tipo de la literal Float
		'''
		return 'float'

def main():
	import sys
	from parser import parse  # Assuming you have a parser that generates the AST
	if len(sys.argv) != 2:
		print('Uso: python3 check.py <archivo>')
		sys.exit(1)
	file = sys.argv[1]
	# Parse the file and wrap the AST in a Program node
	ast_data = parse(file)
	program = Program(ast_data)  # Ensure ast_data is passed as a list of statements
	try:
		systab = Checker.check(program)  # Perform semantic checks
		systab.print()  # Print the symbol table
		print("El programa es semánticamente correcto.")
	except Exception as e:
		print(f"Error semántico: {e}")

def debug():
	from parser import parse 
	file = "Tests/mandelplot.gox"
	ast_data = parse(file)# Parse the file and wrap the AST in a Program node
	program = Program(ast_data)
	print(program)
	try:
		systab = Checker.check(program)  # Perform semantic checks
		systab.print()  # Print the symbol table
		print("El programa es semánticamente correcto.")
	except Exception as e:
		print(f"Error semántico: {e}")

