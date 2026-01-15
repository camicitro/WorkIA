"""
Para que el agente sea realmente "inteligente" y no solo un traductor de Cypher, usaremos Tools (Herramientas). En lugar de que el LLM escriba todo el código, le daremos funciones predefinidas:

Herramienta 1: obtener_perfil_candidato(email)

Herramienta 2: listar_ofertas_disponibles()

Herramienta 3: ejecutar_adecuacion(email_candidato, titulo_oferta)

Esto soluciona el problema de que el LLM "invente" filtros o falle en la sintaxis de grafos complejos


"""
