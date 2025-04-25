# parse.py
#Jose Barco Arias
#Juan David Castaño Vargas
#Estefania Garzón
#
# El analizador debe construir el modelo de
# datos o un árbol de sintaxis abstracta a
# partir de la entrada de texto. La gramática
# aquí se especifica como PEG (Parsing
# Expression Grammar).
#
# PEG Syntax:
#
#    'quoted'   : Texto literal
#    ( ... )    : Agrupacion
#      e?       : Opcional (0 o 1 coincidencia de e)
#      e*       : Repeticion (0 o mas coincidencias de e)
#      e+       : Repeticion (1 o mas coincidencias)
#     e1 e2     : Coincide e1 luego e2 (secuencia)
#    e1 / e2    : Trata e1. Si falla, trata e2.
#
# Se asume que los nombres en mayúsculas son tokens
# del archivo tokenize.py (su analizador lexico).
# EOF es "Fin del archivo".
#
# program <- statement* EOF
#
# statement <- assignment
#           /  vardecl
#           /  funcdel
#           /  if_stmt
#           /  while_stmt
#           /  break_stmt
#           /  continue_stmt
#           /  return_stmt
#           /  print_stmt
#
# assignment <- location '=' expression ';'
#
# vardecl <- ('var'/'const') ID type? ('=' expression)? ';'
#
# funcdecl <- 'import'? 'func' ID '(' parameters ')' type '{' statement* '}'
#
# if_stmt <- 'if' expression '{' statement* '}'
#         /  'if' expression '{' statement* '}' else '{' statement* '}'
#
# while_stmt <- 'while' expression '{' statement* '}'
#
# break_stmt <- 'break' ';'
#
# continue_stmt <- 'continue' ';'
#
# return_stmt <- 'return' expression ';'
#
# print_stmt <- 'print' expression ';'
#
# parameters <- ID type (',' ID type)*
#            /  empty
#
# type <- 'int' / 'float' / 'char' / 'bool'
#
# location <- ID
#          /  '`' expression
#
# expression <- orterm ('||' orterm)*
#
# orterm <- andterm ('&&' andterm)*
#
# andterm <- relterm (('<' / '>' / '<=' / '>=' / '==' / '!=') reltime)*
#
# relterm <- addterm (('+' / '-') addterm)*
#
# addterm <- factor (('*' / '/') factor)*
#
# factor <- literal
#        / ('+' / '-' / '^') expression
#        / '(' expression ')'
#        / type '(' expression ')'
#        / ID '(' arguments ')'
#        / location
#
# arguments <- expression (',' expression)*
#          / empty
#
# literal <- INTEGER / FLOAT / CHAR / bool
#
# bool <- 'true' / 'false'

from rich import print
from typing import List
from dataclasses import dataclass
from source.model import (
    Integer, Float, Char, Bool, TypeCast, BinOp, 
    UnaryOp, Assignment, Variable, NamedLocation, MemoryLocation, 
    Break, Continue, Return, Print, If, While, 
    Function, Parameter, FunctionCall, Program,
)
@dataclass
class Token:
	type  : str
	value : str
	lineno: int = 1
# -------------------------------
# Implementación del Parser
# -------------------------------
class Parser:
	def __init__(self, tokens: List[Token], debug: bool = False):
		self.debug = debug
		self.tokens = tokens
		self.current = 0

	def parse(self) -> Program:
		statements = []
		while self.peek() and self.peek().type != "EOF":
			statements.append(self.statement())
		if self.debug:
			print(statements)
		return Program(statements)

	# -------------------------------
	# Análisis de declaraciones
	# -------------------------------
	def statement(self):
		token = self.peek()
		if token and (token.type == "ID" or token.type == "DEREF"):
			return self.assignment_or_funcCall()
		elif token and (token.type == "VAR" or token.type == "CONST"):
			return self.vardecl()
		elif token and (token.type == "IMPORT" or token.type == "FUNC"):
			return self.funcdecl()
		elif token and token.type == "IF":
			return self.if_stmt()
		elif token and token.type == "WHILE":
			return self.while_stmt()
		elif token and token.type == "BREAK":
			self.consume("BREAK", "Se esperaba 'break'")
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración 'break'")
			return Break()
		elif token and token.type == "CONTINUE":
			self.consume("CONTINUE", "Se esperaba 'continue'")
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración 'continue'")
			return Continue()
		elif token and token.type == "RETURN":
			return self.return_stmt()
		elif token and token.type == "PRINT":
			return self.print_stmt()
		else:
			print(f"ERROR: Token {token}: Declaración inesperada")
			raise SystemExit()
	
	def assignment_or_funcCall(self):
		loc = self.location()
		if self.match("LPAREN"):
			args = self.arguments()
			self.consume("SEMICOLON", "Se esperaba ';' al final de la llamada a la función")
			return FunctionCall(loc.name, args)
		else:
			self.consume("ASSIGN", "Se esperaba '=' en la asignación")
			expr = self.expression()
			self.consume("SEMICOLON", "Se esperaba ';' al final de la asignación")
			return Assignment(loc, expr)
		
	def assignment(self):
		# assignment <- location '=' expression ';'
		loc = self.location()
		self.consume("ASSIGN", "Se esperaba '=' en la asignación")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la asignación")
		return Assignment(loc, expr)
		
	def vardecl(self):
		# vardecl <- ('var'/'const') ID type? ('=' expression)? ';'
		is_const = self.match("CONST")
		if not is_const:
			self.consume("VAR", "Se esperaba 'var' o 'const'")
		var_name = self.consume("ID", "Se esperaba un identificador para la variable").value
		var_type = None
		if self.match("TYPE"):
			var_type = self.tokens[self.current - 1].value
		initial_value = None
		if self.match("ASSIGN"):
			initial_value = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración de variable")
		return Variable(var_name, var_type, initial_value, is_const)
		
	def funcdecl(self):
		# funcdecl <- 'import'? 'func' ID '(' parameters ')' type '{' statement* '}'
		imported = self.match("IMPORT")
		self.consume("FUNC", "Se esperaba 'func'")
		func_name = self.consume("ID", "Se esperaba un identificador para el nombre de la función").value
		self.consume("LPAREN", "Se esperaba '('")
		params = self.parameters()
		self.consume("RPAREN", "Se esperaba ')'")
		func_type = None
		if self.match("TYPE"):
			func_type = self.tokens[self.current - 1].value
		if imported:
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración de importación")
			return Function(imported, func_name, params, func_type, [])
		self.consume("LBRACE", "Se esperaba '{' después de la declaración de la función")
		statements = []
		while not self.match("RBRACE"):
			if not self.peek():  # Check if end of file is reached
				print("ERROR: Se esperaba '}' al final de la declaración de la función")
				raise SystemExit()
			statements.append(self.statement())
		return Function(imported, func_name, params, func_type, statements)
		
	def if_stmt(self):
		# if_stmt <- 'if' expression '{' statement* '}'
		#         /  'if' expression '{' statement* '}' else '{' statement* '}'
		self.consume("IF", "Se esperaba 'if'")
		condition = self.expression()
		self.consume("LBRACE", "Se esperaba '{' después de la condición del 'if'")
		if_statements = []
		while not self.match("RBRACE"):
			if_statements.append(self.statement())
		else_statements = []
		if self.match("ELSE"):
			self.consume("LBRACE", "Se esperaba '{' después de 'else'")
			while not self.match("RBRACE"):
				else_statements.append(self.statement())
		return If(condition, if_statements, else_statements)

	def while_stmt(self):
		# while_stmt <- 'while' expression '{' statement* '}'
		self.consume("WHILE", "Se esperaba 'while'")
		condition = self.expression()
		self.consume("LBRACE", "Se esperaba '{' después de la condición del 'while'")
		statements = []
		while not self.match("RBRACE"):
			statements.append(self.statement())
		return While(condition, statements)
		
	def return_stmt(self):
		# return_stmt <- 'return' expression ';'
		self.consume("RETURN", "Se esperaba 'return'")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración")
		return Return(expr)
		
	def print_stmt(self):
		# print_stmt <- 'print' expression ';'
		self.consume("PRINT", "Se esperaba 'print'")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración")
		return Print(expr)
		
	# -------------------------------
	# Análisis de expresiones
	# -------------------------------
	def expression(self):
		# expression <- orterm ('||' orterm)*
		return self.binary_op(["OR"], "orterm")
		
	def orterm(self):
		# orterm <- andterm ('&&' andterm)*
		return self.binary_op(["AND"], "andterm")
		
	def andterm(self):
		# andterm <- relterm (('<' / '>' / '<=' / '>=' / '==' / '!=') relterm)*
		return self.binary_op(["LT", "GT", "LE", "GE", "EQ", "NE"], "relterm")
		
	def relterm(self):
		# relterm <- addterm (('+' / '-') addterm)*
		return self.binary_op(["PLUS", "MINUS"], "addterm")
		
	def addterm(self):
		# addterm <- factor (('*' / '/') factor)*
		return self.binary_op(["MUL", "DIV"], "factor")
	
	def binary_op(self, operators, next_rule):
		# binary_op <- next_rule (operators next_rule)*
		left = getattr(self, next_rule)()
		while self.peek() and self.peek().type in operators:
			operator = self.advance().value
			right = getattr(self, next_rule)()
			left = BinOp(operator, left, right)
		return left
		
	def factor(self):
		# factor <- literal
		#        / ('+' / '-' / '^') expression
		#        / '(' expression ')'
		#        / type '(' expression ')'
		#        / ID '(' arguments ')'
		#        / location
		if self.match("INTEGER"):
			return Integer(self.tokens[self.current - 1].value)
		elif self.match("FLOAT"):
			return Float(self.tokens[self.current - 1].value)
		elif self.match("CHAR"):
			return Char(self.tokens[self.current - 1].value)
		elif self.match("BOOL"):
			return Bool(self.tokens[self.current - 1].value)
		elif self.match("PLUS") or self.match("MINUS") or self.match("CARET") or self.match("NOT"):
			operator = self.tokens[self.current - 1].value
			expr = self.factor()
			return UnaryOp(operator, expr)
		elif self.match("LPAREN"):
			expr = self.expression()
			self.consume("RPAREN", "Se esperaba ')' después de la expresión")
			return expr
		elif self.match("TYPE"):
			cast_type = self.tokens[self.current - 1].value
			self.consume("LPAREN", "Se esperaba '(' después del tipo")
			expr = self.expression()
			self.consume("RPAREN", "Se esperaba ')' después de la expresión")
			return TypeCast(cast_type, expr)
		elif self.match("ID"):
			func_or_loc = self.tokens[self.current - 1].value
			if self.match("LPAREN"):
				args = self.arguments()
				return FunctionCall(func_or_loc, args)
			else:
				return NamedLocation(func_or_loc)
		else:
			return self.location()
		
	def parameters(self):
		# parameters <- ID type (',' ID type)*
		#            /  empty
		params = []
		if self.peek() and self.peek().type != "RPAREN":  # Check if parameters are empty
			while True:
				param_name = self.consume("ID", "Se esperaba un identificador para el parámetro").value
				param_type = self.consume("TYPE", "Se esperaba un tipo para el parámetro").value
				params.append(Parameter(param_name, param_type))
				if not self.match("COMMA"):  # If no comma, break the loop
					break
		return params
		
	def arguments(self): 
		# arguments <- expression (',' expression)*
		#          / empty
		args = []
		if not self.match("RPAREN"):  # Check if arguments are empty
			while True:
				args.append(self.expression())
				if not self.match("COMMA"):  # If no comma, break the loop
					break
			self.consume("RPAREN", "Se esperaba ')' después de los argumentos")
		return args
	
	def location(self):
		# location <- ID
		#          /  '`' expression
		if self.match("ID"):
			return NamedLocation(self.tokens[self.current - 1].value)
		elif self.match("DEREF"):
			expr = self.expression()
			return MemoryLocation(expr)
		else:
			print(f"ERROR: {self.peek()}")
			raise SystemExit(f"Se esperaba un identificador o una expresión entre paréntesis")

	# -------------------------------
	# Trate de conservar este codigo
	# -------------------------------

	def peek(self) -> Token:
		return self.tokens[self.current] if self.current < len(self.tokens) else None
		
	def advance(self) -> Token:
		token = self.peek()
		self.current += 1
		return token
		
	def match(self, token_type: str) -> bool:
		token = self.peek()
		if token and token.type == token_type:
			self.advance()
			return True
		return False
		
	def consume(self, token_type: str, message: str):
		if self.match(token_type):
			return self.tokens[self.current - 1]
		print(f"ERROR: {message}, se encontro: Token {self.peek()}")
		raise SystemExit()

# Convertir el AST a una representación JSON para mejor visualización
import json
class ASTSerializer:
	@staticmethod
	def ast_to_dict(node):
		if isinstance(node, list):
			return [ASTSerializer.ast_to_dict(item) for item in node]
		elif hasattr(node, "__dict__"):
			return {key: ASTSerializer.ast_to_dict(value) for key, value in node.__dict__.items()}
		else:
			return node

	@staticmethod
	def save_ast_to_json(ast, file_path="ast_updated.json"):
		ast_json = json.dumps(ASTSerializer.ast_to_dict(ast), indent=4)
		with open(file_path, "w", encoding="utf-8") as f:
			f.write(ast_json)
		return file_path


# -------------------------------
# Prueba del Parser con Tokens
# -------------------------------
testTokens = [
	Token('FUNC', 'func', 1),
	Token('ID', 'main', 1),
	Token('LPAREN', '(', 1),
	Token('ID', 'abc', 1),
	Token('TYPE', 'int', 1),
	Token('RPAREN', ')', 1),
	Token('LBRACE', '{', 1),
	Token('PRINT', 'print', 3),
	Token('LPAREN', '(', 3),
	Token('CHAR', "'a'", 3),
	Token('RPAREN', ')', 3),
	Token('SEMICOLON', ';', 3),
	Token('RBRACE', '}', 22)
]
testTokens2 = [
	Token(type='VAR', value='var', lineno=1),
	Token(type='ID', value='x', lineno=1),
	Token(type='TYPE', value='int', lineno=1),
	Token(type='ASSIGN', value='=', lineno=1),
	Token(type='CARET', value='^', lineno=1),
	Token(type='INTEGER', value='8192', lineno=1),
	Token(type='SEMICOLON', value=';', lineno=1),
	Token(type='VAR', value='var', lineno=2),
	Token(type='ID', value='addr', lineno=2),
	Token(type='TYPE', value='int', lineno=2),
	Token(type='ASSIGN', value='=', lineno=2),
	Token(type='INTEGER', value='1234', lineno=2),
	Token(type='SEMICOLON', value=';', lineno=2),
	Token(type='DEREF', value='`', lineno=3),
	Token(type='ID', value='addr', lineno=3),
	Token(type='ASSIGN', value='=', lineno=3),
	Token(type='INTEGER', value='5678', lineno=3),
	Token(type='SEMICOLON', value=';', lineno=3),
	Token(type='PRINT', value='print', lineno=4),
	Token(type='LPAREN', value='(', lineno=4),
	Token(type='DEREF', value='`', lineno=4),
	Token(type='ID', value='addr', lineno=4),
	Token(type='PLUS', value='+', lineno=4),
	Token(type='INTEGER', value='8', lineno=4),
	Token(type='RPAREN', value=')', lineno=4),
	Token(type='SEMICOLON', value=';', lineno=4),
]

def parser_test():
	parser = Parser(testTokens2)
	ast = parser.parse()
	# Guardar el AST como JSON
	ast_file_path = ASTSerializer.save_ast_to_json(ast)
	return ast_file_path

def parse_text(content):
	# Crear el analizador lexico
	from lexer import Lexer
	lex = Lexer()
	# Leer el archivo de entrada
	fileTokens = lex.tokenize(content)
	parser = Parser(fileTokens)
	ast = parser.parse()
	# Guardar el AST como JSON
	ast_file_path = ASTSerializer.save_ast_to_json(ast)
	return ast_file_path

def parse(file_path):
	# Crear el analizador lexico
	from lexer import Lexer
	lex = Lexer()
	# Leer el archivo de entrada
	with open(file_path, "r", encoding="utf-8") as file:
		content = file.read()
	fileTokens = lex.tokenize(content)
	parser = Parser(fileTokens)
	ast_data = parser.parse()  # Devuelve directamente el AST como una lista de objetos
	return ast_data

def parse_file(file_path):
	# Crear el analizador lexico
	from lexer import Lexer
	lex = Lexer()
	# Leer el archivo de entrada
	with open(file_path, "r", encoding="utf-8") as file:
		content = file.read()
	fileTokens = lex.tokenize(content)
	parser = Parser(fileTokens)
	ast = parser.parse()
	# Guardar el AST como JSON
	ast_file_path = ASTSerializer.save_ast_to_json(ast, file_path.replace(".gox", "_ast.json"))
	return ast_file_path

def main(argv):
	if len(argv) != 2:
		raise SystemExit(f"Usage py parser.py <input_file>")
	file_path = argv[1]
	ast_file_path = parse_file(file_path)

if __name__ == "__main__":
	import sys
	parser_test()
	#main(sys.argv)

