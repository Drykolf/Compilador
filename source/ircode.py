# ircode.py
'''
Una Máquina Intermedia "Virtual"
================================

Una CPU real generalmente consta de registros y un pequeño conjunto de
códigos de operación básicos para realizar cálculos matemáticos,
cargar/almacenar valores desde memoria y controlar el flujo básico
(ramas, saltos, etc.). Aunque puedes hacer que un compilador genere
instrucciones directamente para una CPU, a menudo es más sencillo
dirigirse a un nivel de abstracción más alto. Una de esas abstracciones
es la de una máquina de pila (stack machine).

Por ejemplo, supongamos que deseas evaluar una operación como esta:

    a = 2 + 3 * 4 - 5

Para evaluar la expresión anterior, podrías generar pseudo-instrucciones
como esta:

    CONSTI 2      ; stack = [2]
    CONSTI 3      ; stack = [2, 3]
    CONSTI 4      ; stack = [2, 3, 4]
    MULI          ; stack = [2, 12]
    ADDI          ; stack = [14]
    CONSTI 5      ; stack = [14, 5]
    SUBI          ; stack = [9]
    LOCAL_SET "a" ; stack = []

Observa que no hay detalles sobre registros de CPU ni nada por el estilo
aquí. Es mucho más simple (un módulo de nivel inferior puede encargarse
del mapeo al hardware más adelante si es necesario).

Las CPUs usualmente tienen un pequeño conjunto de tipos de datos como
enteros y flotantes. Existen instrucciones dedicadas para cada tipo. El
código IR seguirá el mismo principio, admitiendo operaciones con enteros
y flotantes. Por ejemplo:

    ADDI   ; Suma entera
    ADDF   ; Suma flotante

Aunque el lenguaje de entrada podría tener otros tipos como `bool` y
`char`, esos tipos deben ser mapeados a enteros o flotantes. Por ejemplo,
un bool puede representarse como un entero con valores {0, 1}. Un char
puede representarse como un entero cuyo valor sea el mismo que el código
del carácter (es decir, un código ASCII o código Unicode).

Con eso en mente, aquí hay un conjunto básico de instrucciones para
nuestro Código IR:

    ; Operaciones enteras
    CONSTI value             ; Apilar un literal entero
    ADDI                     ; Sumar los dos elementos superiores de la pila
    SUBI                     ; Restar los dos elementos superiores de la pila
    MULI                     ; Multiplicar los dos elementos superiores de la pila
    DIVI                     ; Dividir los dos elementos superiores de la pila
    ANDI                     ; AND bit a bit
    ORI                      ; OR bit a bit
    LTI                      : <
    LEI                      : <=
    GTI                      : >
    GEI                      : >=
    EQI                      : ==
    NEI                      : !=
    PRINTI                   ; Imprimir el elemento superior de la pila
    PEEKI                    ; Leer entero desde memoria (dirección en la pila)
    POKEI                    ; Escribir entero en memoria (valor, dirección en la pila)
    ITOF                     ; Convertir entero a flotante

    ; Operaciones en punto flotante
    CONSTF value             ; Apilar un literal flotante
    ADDF                     ; Sumar los dos elementos superiores de la pila
    SUBF                     ; Restar los dos elementos superiores de la pila
    MULF                     : Multiplicar los dos elementos superiores de la pila
    DIVF                     : Dividir los dos elementos superiores de la pila
    LTF                      : <
    LEF                      : <=
    GTF                      : >
    GEF                      : >=
    EQF                      : ==
    NEF                      : !=
    PRINTF                   ; Imprimir el elemento superior de la pila
    PEEKF                    ; Leer flotante desde memoria (dirección en la pila)
    POKEF                    ; Escribir flotante en memoria (valor, dirección en la pila)
    FTOI                     ; Convertir flotante a entero

    ; Operaciones orientadas a bytes (los valores se presentan como enteros)
    PRINTB                   ; Imprimir el elemento superior de la pila
    PEEKB                    ; Leer byte desde memoria (dirección en la pila)
    POKEB                    ; Escribir byte en memoria (valor, dirección en la pila)

    ; Carga/almacenamiento de variables.
    ; Estas instrucciones leen/escriben variables locales y globales. Las variables
    ; son referenciadas por algún tipo de nombre que las identifica. La gestión
    ; y declaración de estos nombres también debe ser manejada por tu generador de código.
    ; Sin embargo, las declaraciones de variables no son una instrucción normal. En cambio,
    ; es un tipo de dato que debe asociarse con un módulo o función.
    LOCAL_GET name           ; Leer una variable local a la pila
    LOCAL_SET name           ; Guardar una variable local desde la pila
    GLOBAL_GET name          ; Leer una variable global a la pila
    GLOBAL_SET name          ; Guardar una variable global desde la pila

    ; Llamadas y retorno de funciones.
    ; Las funciones se referencian por nombre. Tu generador de código deberá
    ; encontrar alguna manera de gestionar esos nombres.
    CALL name                ; Llamar función. Todos los argumentos deben estar en la pila
    RET                      ; Retornar de una función. El valor debe estar en la pila

    ; Control estructurado de flujo
    IF                       ; Comienza la parte "consecuencia" de un "if". Prueba en la pila
    ELSE                     ; Comienza la parte "alternativa" de un "if"
    ENDIF                    ; Fin de una instrucción "if"

    LOOP                     ; Inicio de un ciclo
    CBREAK                   ; Ruptura condicional. Prueba en la pila
    CONTINUE                 ; Regresa al inicio del ciclo
    ENDLOOP                  ; Fin del ciclo

    ; Memoria
    GROW                     ; Incrementar memoria (tamaño en la pila) (retorna nuevo tamaño)

Una palabra sobre el acceso a memoria... las instrucciones PEEK y POKE
se usan para acceder a direcciones de memoria cruda. Ambas instrucciones
requieren que una dirección de memoria esté en la pila *primero*. Para
la instrucción POKE, el valor a almacenar se apila después de la dirección.
El orden es importante y es fácil equivocarse. Así que presta mucha
atención a eso.

Su tarea
=========
Su tarea es la siguiente: Escribe código que recorra la estructura del
programa y la aplane a una secuencia de instrucciones representadas como
tuplas de la forma:

       (operation, operands, ...)

Por ejemplo, el código del principio podría terminar viéndose así:

    code = [
       ('CONSTI', 2),
       ('CONSTI', 3),
       ('CONSTI', 4),
       ('MULI',),
       ('ADDI',),
       ('CONSTI', 5),
       ('SUBI',),
       ('LOCAL_SET', 'a'),
    ]

Funciones
=========
Todo el código generado está asociado con algún tipo de función. Por
ejemplo, con una función definida por el usuario como esta:

    func fact(n int) int {
        var result int = 1;
        var x int = 1;
        while x <= n {
            result = result * x;
            x = x + 1;
        }
     }

Debes crear un objeto `Function` que contenga el nombre de la función,
los argumentos, el tipo de retorno, las variables locales y un cuerpo
que contenga todas las instrucciones de bajo nivel. Nota: en este nivel,
los tipos representarán tipos IR de bajo nivel como Integer (I) y Float (F).
No son los mismos tipos usados en el código GoxLang de alto nivel.

Además, todo el código que se define *fuera* de una función debe ir
igualmente en una función llamada `_init()`. Por ejemplo, si tienes
declaraciones globales como esta:

     const pi = 3.14159;
     const r = 2.0;
     print pi*r*r;

Tu generador de código debería en realidad tratarlas así:

     func _init() int {
         const pi = 3.14159;
         const r = 2.0;
         print pi*r*r;
         return 0;
     }

En resumen: todo el código debe ir dentro de una función.

Módulos
=======
La salida final de la generación de código debe ser algún tipo de
objeto `Module` que contenga todo. El módulo incluye objetos de función,
variables globales y cualquier otra cosa que puedas necesitar para
generar código posteriormente.
'''
from rich   import print
from typing import List, Union
from functools import singledispatchmethod
from source.model  import *
from source.symtab import Symtab
from source.typesys import typenames, check_binop, check_unaryop

# Todo el código IR se empaquetará en un módulo. Un 
# módulo es un conjunto de funciones.

class IRModule:
	def __init__(self):
		self.functions = { }       # Dict de funciones IR 
		self.globals = { }         # Dict de variables global
		
	def dump(self):
		print("MODULE:::")
		for glob in self.globals.values():
			glob.dump()
			
		for func in self.functions.values():
			func.dump()
			
# Variables Globales
class IRGlobal:
	def __init__(self, name, type):
		self.name = name
		self.type = type
		
	def dump(self):
		print(f"GLOBAL::: {self.name}: {self.type}")

# Las funciones sirven como contenedor de las 
# instrucciones IR de bajo nivel específicas de cada
# función. También incluyen metadatos como el nombre 
# de la función, los parámetros y el tipo de retorno.

class IRFunction:
	def __init__(self, module, name, parmnames, parmtypes, return_type, imported=False):
		# Agreguemos la lista de funciones del módulo adjunto
		self.module = module
		module.functions[name] = self
		
		self.name = name
		self.parmnames = parmnames
		self.parmtypes = parmtypes
		self.return_type = return_type
		self.imported = imported
		self.locals = { }    # Variables Locales
		self.code = [ ]      # Lista de Instrucciones IR 
		
	def new_local(self, name, type):
		self.locals[name] = type
		
	def append(self, instr):
		self.code.append(instr)
		
	def extend(self, instructions):
		self.code.extend(instructions)
		
	def dump(self):
		print(f"FUNCTION::: {self.name}, {self.parmnames}, {self.parmtypes} {self.return_type}")
		print(f"locals: {self.locals}")
		for instr in self.code:
			print(instr)
			
# Mapeo de tipos de GoxLang a tipos de IR
_typemap = {
	'int'  : 'I',
	'float': 'F',
	'bool' : 'I',
	'char' : 'I',
}

# Generar un nombre de variable temporal único
def new_temp(n=[0]):
	n[0] += 1
	return f'$temp{n[0]}'

# Una función de nivel superior que comenzará a generar IRCode

class IRCode(Visitor):
	_binop_code = {
		('int', '+', 'int')  : 'ADDI',
		('int', '-', 'int')  : 'SUBI',
		('int', '*', 'int')  : 'MULI',
		('int', '/', 'int')  : 'DIVI',
		('int', '<', 'int')  : 'LTI',
		('int', '<=', 'int') : 'LEI',
		('int', '>', 'int')  : 'GTI',
		('int', '>=', 'int') : 'GEI',
		('int', '==', 'int') : 'EQI',
		('int', '!=', 'int') : 'NEI',
		
		('float', '+',  'float') : 'ADDF',
		('float', '-',  'float') : 'SUBF',
		('float', '*',  'float') : 'MULF',
		('float', '/',  'float') : 'DIVF',
		('float', '<',  'float') : 'LTF',
		('float', '<=', 'float') : 'LEF',
		('float', '>',  'float') : 'GTF',
		('float', '>=', 'float') : 'GEF',
		('float', '==', 'float') : 'EQF',
		('float', '!=', 'float') : 'NEF',
		
		('char', '<', 'char')  : 'LTI',
		('char', '<=', 'char') : 'LEI',
		('char', '>', 'char')  : 'GTI',
		('char', '>=', 'char') : 'GEI',
		('char', '==', 'char') : 'EQI',
		('char', '!=', 'char') : 'NEI',
	}
	_unaryop_code = {
		('+', 'int')   : [],
		('+', 'float') : [],
		('-', 'int')   : [('CONSTI', -1), ('MULI',)],
		('-', 'float') : [('CONSTF', -1.0), ('MULF',)],
		('!', 'bool')  : [('CONSTI', -1), ('MULI',)],
		('^', 'int')   : [ ('GROW',) ]
	}
	_typecast_code = {
		# (from, to) : [ ops ]
		('int', 'float') : [ ('ITOF',) ],
		('float', 'int') : [ ('FTOI',) ],
	}

	@classmethod
	def gencode(cls, node:List[Statement]):
		'''
		El nodo es el nodo superior del árbol de 
		modelo/análisis.
		La función inicial se llama "_init". No acepta 
		argumentos. Devuelve un entero.
		'''
		ircode = cls()

		cls.module = IRModule()

		func = IRFunction(cls.module, 'main', [], [], 'I')
		# Then process statements in main function
		for item in node:
			item.accept(ircode, func)
		if '_actual_main' in cls.module.functions:
			func.append(('CALL', '_actual_main'))
		else:
			func.append(('CONSTI', 0))
		func.append(('RET',))
		return cls.module

	# --- Statements
	@singledispatchmethod
	def visit(self, n, func):
		# Si no se encuentra un nodo, se lanza una excepción
		raise Exception(f"Error: No se puede visitar el nodo {n.__class__.__name__} en IRCode")
	
	@visit.register
	def _(self, n: Assignment, func: IRFunction):
		# Visitar n.expr
		# Visitar n.loc (tener en cuenta set/get)
		n.location.usage = 'store'
		n.expression.usage = 'load'
		n.location.store_value = n.expression
		n.location.accept(self, func)
	
	@visit.register
	def _(self, n: Print, func: IRFunction):
		type = n.expr.accept(self, func)
		if type == 'int' or type in ['bool','true', 'false']:
			func.append(('PRINTI',))
		elif type == 'float':
			func.append(('PRINTF',))
		elif type == 'char':
			func.append(('PRINTB',))

	@visit.register
	def _(self, n: If, func: IRFunction):
		# Visitar n.condition
		n.condition.accept(self, func)
		func.append(('IF',))
		# Procesar las instrucciones en la parte de la consecuencia (then)
		for stmt in n.if_statements:
			stmt.accept(self, func)
		func.append(('ELSE',))
		# Procesar las instrucciones en la parte alternativa (else)
		for stmt in n.else_statements:
			stmt.accept(self, func)
		func.append(('ENDIF',))

	@visit.register
	def _(self, n: While, func: IRFunction):
		func.append(('LOOP',))
		func.append(('CONSTI', 1))
		# Visitar n.test
		n.condition.accept(self, func)
		func.append(('SUBI',))
		func.append(('CBREAK',))
		# Visitar n.body
		for stmt in n.statements:
			stmt.accept(self, func)
		func.append(('ENDLOOP',))

	@visit.register
	def _(self, n: Break, func: IRFunction):
		func.append(('CONSTI', 1))
		func.append(('CBREAK',))

	@visit.register
	def _(self, n: Continue, func: IRFunction):
		func.append(('CONTINUE',))

	@visit.register
	def _(self, n: Return, func: IRFunction):
		# First visit the return expression to push its value onto the stack
		if n.expr:
			n.expr.accept(self, func)
		else:
			# If there's no return expression, push a default value (0)
			func.append(('CONSTI', 0))
		# Then append the return instruction
		func.append(('RET',))

	# --- Declaration
		
	@visit.register
	def _(self, n: Variable, func: IRFunction):
		irtype = _typemap.get(n.type, 'I')
		if func.name == 'main':  # Variables globales
			self.module.globals[n.name] = IRGlobal(n.name, irtype)
			if n.value:
				n.value.accept(self, func)
				func.append(('GLOBAL_SET', n.name))
			return
		func.new_local(n.name, irtype)
		# Visit the initializer if it exists
		if n.value:
			n.value.accept(self, func)
			func.append(('LOCAL_SET', n.name))
		
	@visit.register
	def _(self, n: Function, func: IRFunction):
		'''
		Si encontramos una nueva función, tenemos que suspender la
		generación de código para la función actual "func" y crear
		una nueva función
		'''
		parmnames = [p.name for p in n.params]
		parmtypes = [_typemap[p.type] for p in n.params]
		rettype   = _typemap[n.func_type]

		if n.name == 'main':
			name = '_actual_main'
		else:
			name = n.name
		
		newfunc = IRFunction(
			func.module,
			name,
			parmnames,
			parmtypes,
			rettype,
			n.imported
		)
		for p in n.params:newfunc.new_local(p.name, _typemap[p.type])
		if not n.imported:
			# Visitar n.stmts
			for stmt in n.statements:
				stmt.accept(self, newfunc)
		
	# --- Expressions
	
	@visit.register
	def _(self, n: Integer, func: IRFunction):
		func.append(('CONSTI', n.value))
		return "int"

	@visit.register
	def _(self, n: Float, func: IRFunction):
		func.append(('CONSTF', n.value))
		return "float"

	@visit.register
	def _(self, n: Char, func: IRFunction):
		func.append(('CONSTI', ord(n.value)))
		#func.append(('CONSTI', ord('\\xff')))
		return "char"
		
	@visit.register
	def _(self, n: Bool, func: IRFunction):
		boolValue = 1 if n.value == "true" else 0
		func.append(('CONSTI', boolValue))
		return "bool"
	
	@visit.register
	def _(self, n: BinOp, func: IRFunction):
		if n.operator == '&&':
			# short-circuit: Si n.left es false, hasta aca llega
			left=True
			n.left.accept(self, func)
			func.append(('CONSTI', 0))
			func.append(('EQI',))
			func.append(('CBREAK',))
			if not left:
				func.append(('ANDI',))
				return "bool"
			n.right.accept(self, func)
			func.append(('ANDI',))
			return "bool"
		
		elif n.operator == '||':
			# short-circuit: si n.left es true, hasta aca llega
			left = False
			n.left.accept(self, func)
			func.append(('CONSTI', 0))
			func.append(('NEI',))
			func.append(('CBREAK',))
			if left:
				func.append(('ORI',))
				return "bool"
			n.right.accept(self, func)
			func.append(('ORI',))
			return "bool"
		else:
			leftT = n.left.accept(self, func)
			rightT = n.right.accept(self, func)
			func.append((self._binop_code[leftT, n.operator, rightT],))
			return check_binop(n.operator, leftT, rightT)
		
	@visit.register
	def _(self, n: UnaryOp, func: IRFunction):
		# Visitar n.expr
		type = n.operand.accept(self, func)
		func.extend((self._unaryop_code[n.operator, type],))
		return type
		
	@visit.register
	def _(self, n: TypeCast, func: IRFunction):
		# Visitar n.expr
		_type = n.expr.accept(self, func)
		if _type != n.cast_type:
			func.extend(self._typecast_code[_type, n.cast_type])
		return n.cast_type

	@visit.register
	def _(self, n: FunctionCall, func: IRFunction):
		# Visitar n.args
		func.append(('CALL', n.name))
	
	@visit.register
	def _(self, n: NamedLocation, func: IRFunction):
		# Determinar si la variable es global o local
		is_global = n.name in func.module.globals
		try:
			if n.usage == 'store':
				n.store_value.accept(self, func)
				# Si es una variable global, se almacena en la tabla de símbolos
				if is_global: func.append(('GLOBAL_SET', n.name))
				else: func.append(('LOCAL_SET', n.name))
				return
		except AttributeError:
			pass
		# Si no es una asignación, se carga la variable
		if is_global:
			_type = func.module.globals[n.name].type
			func.append(('GLOBAL_GET', n.name))
		else:
			_type = func.locals[n.name]
			func.append(('LOCAL_GET', n.name))
		# Retornar el tipo de la variable
		return "float" if _type == 'F' else "int"

	@visit.register
	def _(self, n: MemoryLocation, func: IRFunction):
		try:
			if n.usage == 'store':
				# Visitar n.address
				# Visitar n.store_value (agregado en nodo Assignment)
				_type = n.expr.accept(self, func)
				n.store_value.accept(self, func)
				if _type in {'int', 'bool'}:
					func.append(('POKEI',))
				elif _type == 'float':
					func.append(('POKEF',))
				elif _type == 'char':
					func.append(('POKEB',))
				return
		except AttributeError:
			pass
		# Visitar n.address
		_type = n.expr.accept(self, func)
		if _type in {'int', 'bool'}:
			func.append(('PEEKI',))
		elif _type == 'float':
			func.append(('PEEKF',))
		elif _type == 'char':
			func.append(('PEEKB',))


