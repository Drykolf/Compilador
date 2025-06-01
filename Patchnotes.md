# v0.3:
### Maquina de Pila:

## General:
1. Se agrego un archivo nuevo de configuracion, para indicar facilmente cuando estamos haciendo pruebas y necesitamos ver mas informacion (debug, imprimir todas las salidas de los analizadores).
2. A todos los analizadores se les agregaron condicionales para que generen un archivo con sus resultados.
3. Se arreglaron errores ligeros encontrados en algunos de los analizadores.

# v0.2:
### Lexer:
1. Se modificó en el Lexer.py, la funcion process_char_literal, porque en el IRcode no agarraba bien el token del char, entonces la funcion nueva procesa la cadena del caracter y lo deja en un formato que si puede procesar la funcion ord de python.

### IRcode:
1. Se añadieron decoradores de singledispatchmethod, en los visit para que puedieran compartir el mismo nombre todos los metodos, sin eso no funcionaba bien el programa ya que siempre agarraba el ultimo metodo visit definido
2. Todos los metodos se completaron de acuerdo a los comentarios del profesor
3. Se agregaron return del tipo "int, bool, float, char" en los metodos de cada tipo, y en otros como BinOp, UnaryOp, Typecast
4. MemoryLocation agrega tuplas dependiendo si es llamado para almacenar o cargar
5. NamedLocation igual verifica si es en carga o almacenamiento, ademas verifica si es location global o local
6. Function crea una nueva IRFunction, y le mete los parametros en la lista de variables locales, y si no es importada, recorre sus statements
7. Variable, agrega las variables a la tabla de variables globales si no se esta dentro ninguna funcion, sino seria variables locales


# v0.1
### Checker:
1. En el archivo model.py toco agregar una clase Nodo con un metodo accept, y a todas las clases hacer que heredaran de Nodo.
2. En el archivo tyesys.py toco agregar a las operaciones binarias, las de asignacion
3. symtab no se hizo nada creo
4. check.py Se hizo el main que pasa un programa por Parser, y agarra el resultante
5. Se añadieron decoradores de singledispatchmethod, en los visit para que puedieran compartir el mismo nombre todos los metodos, sin eso no funcionaba bien el programa ya que siempre agarraba el ultimo metodo visit definido
6. Se completaron todos los metodos visit de acuerdo a los comentarios del profesor
7. En los metodos Funcion, while, if, se crean tablas nuevas internas


# v0
## Parser y lexer:
* lexer.py ya estaba hecho, fue como la primera tarea para pasar un codigo a tokens
* model.py fue una tarea pasada tambien, se hicieron modificaciones para que los nombres de las clases coincidan con los de parser.py, y tambien se agrego una propiedad "self.definition" en todas las clases para facilitar la lectura en el arbol json
### En parser.py:
* los metodos peek, advance, consume, match, ya los entregó el profe hechos
* los demas metodos para la gramatica estaban definidos pero vacios, simplemente era ir completandolos, haciendo uso de las funciones peek, advance, consume, match; e ir avanzando en la lista de tokens.
* hubo un par de metodos que toco crear, no estaban ahi puestos, el location, y el arguments.
* en el metodo statement, se cambiaron todos los match() por un peek(), para que no avanzara en la lista de tokens, y ya cada funcion especifica consumia el token que se habia mirado|
* los metodos para armar y mostrar el ast en json, ya estaban ahi, los dio el profe
* se hicieron varias pruebas con textos distintos, entre ellos los 8 que habiamos usado en la tarea anterior