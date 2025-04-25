#Jose Barco Arias
#Juan David Castaño Vargas
#Estefania Garzón

import re
from rich import print
from dataclasses import dataclass
KEYWORDS = {"const": "CONST",
            "var": "VAR",
            "print": "PRINT",
            "return": "RETURN",
            "break": "BREAK",
            "continue": "CONTINUE",
            "if": "IF",
            "else": "ELSE",
            "while": "WHILE",
            "func": "FUNC",
            "import": "IMPORT",
            "true": "BOOL",
            "false": "BOOL",
            "int": "TYPE",
            "float": "TYPE",
            "char": "TYPE",
            "bool": "TYPE"}#palabras reservadas
INT_PATTERN = re.compile(r"\d+")
FLOAT_PATTERN = re.compile(r"(\d+\.\d*)|(\d*\.\d+)")
CHAR_PATTERN = re.compile(r"'(\\.|\\x[A-Za-z0-9]+|.)'")#'a' '\\n' '\\x41' '\\''
TWO_CHAR_TOKENS = {"<=": "LE",
                    ">=": "GE",
                    "==": "EQ",
                    "!=": "NE",
                    "&&": "AND",
                    "||": "OR"}
ONE_CHAR_TOKENS = {"^": "CARET",
                    "+": "PLUS",
                    "-": "MINUS",
                    "*": "MUL",
                    "/": "DIV",
                    "<": "LT",
                    ">": "GT",
                    "=": "ASSIGN",
                    ";": "SEMICOLON",
                    "(": "LPAREN",
                    ")": "RPAREN",
                    "{": "LBRACE",
                    "}": "RBRACE",
                    ",": "COMMA",
                    "!": "NOT",
                    "`": "DEREF"}#` es el simbolo de puntero

@dataclass
class Token:
  type  : str
  value : str
  lineno: int = 1

class Lexer:
    def __init__(self, debug=False):
        self.debug = debug
        self.hasErrors = False
        
    def scan(self, text):
        index = 0 #indice de texto
        lineno = 1 #contador de linea
        while index < len(text):
            if text[index] in " \t":  # caracteres a ignorar (whitespace, tab)
                index += 1
                continue
            elif text[index:index+2] == "//":  # Comentarios de una linea
                index = text.find("\n", index)
                if index == -1:  # If no newline found, we are at the end of text
                    break
                continue
            elif text[index:index+2] == "/*":  # Comentarios de varias lineas
                start = index
                index = text.find("*/", index)
                if index == -1:
                    print(f"ERROR: COMENTARIO NO TERMINADO EN LINEA {lineno}")
                    self.hasErrors = True
                    break
                lineno += text[start:index].count("\n")
                index += 2
                continue
            elif text[index] == "\n":
                index += 1
                lineno += 1
                continue
            elif text[index].isalpha() or text[index] == '_':  # Identificadores
                start = index
                while index < len(text) and (text[index].isalnum() or text[index] == '_'):
                    index += 1
                if text[start:index] in KEYWORDS:
                    yield Token(KEYWORDS[text[start:index]], text[start:index], lineno)
                    continue
                yield Token("ID", text[start:index], lineno)
                continue
            elif text[index].isdigit() or text[index] == '.':  # Literales numericos
                match = FLOAT_PATTERN.match(text, index)
                if match:
                    yield Token("FLOAT", match.group(), lineno)
                    index = match.end()
                    continue
                match = INT_PATTERN.match(text, index)
                if match:
                    yield Token("INTEGER", match.group(), lineno)
                    index = match.end()
                    continue
            elif text[index] == "'":  # Literales de caracter
                match = CHAR_PATTERN.match(text, index)
                if match:
                    yield Token("CHAR", match.group(), lineno)
                    index = match.end()
                    continue
                else:
                    print(f"ERROR: Caracter invalido '{text[index]}' en linea {lineno}")
                    self.hasErrors = True
                    index += 1
            elif text[index] in "+-*/<=>!&|^;(){},`!":  # operadores y simbolos
                start = index
                index += 1
                if text[start:index+1] in ["<=", ">=", "==", "!=", "&&", "||"]:  # Operadores de dos caracteres
                    index += 1
                    yield Token(TWO_CHAR_TOKENS[text[start:index]], text[start:index], lineno)
                    continue
                yield Token(ONE_CHAR_TOKENS[text[start]], text[start:index], lineno)
                continue
            else:
                print(f"ERROR: Caracter invalido '{text[index]}' en linea {lineno}")
                self.hasErrors = True
                index += 1

    def tokenize(self, text):
        #scanner = re.Scanner(self.tokens)
        try:
            raw = self.scan(text)
            results = list(raw)
            if self.hasErrors:
                raise SyntaxError("Errores lexicos encontrados!")
            return results
        except SyntaxError as e:
            raise SyntaxError(e)
