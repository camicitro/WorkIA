import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class Neo4jService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        self.driver.close()


    # Helper
    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]


    # --- CONSULTAR DATOS ---
    def search_candidates(self, criterio):
        query = """
            MATCH (c:Candidato) 
            WHERE c.nombre CONTAINS $criterio OR c.apellido CONTAINS $criterio
            RETURN c.nombre, c.apellido, c.email
        """
        return self.run_query(query, {"criterio": criterio})

    def get_candidate_profile(self, email):
        #Extrae datos, habilidades y experiencia de un candidato.
        query = """
        MATCH (c:Candidato {email: $email})
        OPTIONAL MATCH (c)-[p:POSEE]->(h:Habilidad)
        WITH c, collect({nombre: h.nombre, nivel: p.nivel, ultimo_uso: p.ultimo_uso, tipo: h.tipo}) AS habilidades
        OPTIONAL MATCH (c)-[t:TRABAJO_EN]->(e:Empresa)
        RETURN c.nombre + ' ' + c.apellido AS nombre_completo,
               c.email AS email,
               c.ubicacion AS ubicacion,
               c.fecha_nacimiento AS fecha_nacimiento,
               c.movilidad AS movilidad,
               c.seniority AS seniority,
               habilidades,
               collect({puesto: t.puesto, fecha_inicio: t.fecha_inicio, fecha_fin: t.fecha_fin}) AS experiencias
        """
        result = self.run_query(query, {"email": email})
        return result[0] if result else None

    def get_offer_requirements(self, titulo):
        #TODO: ver si agrego: meses_min_experiencia: toInteger($detalles.meses_min_experiencia),
        query = """
        MATCH (o:Oferta) WHERE o.titulo CONTAINS $titulo
        OPTIONAL MATCH (o)-[r:REQUIERE]->(h:Habilidad)
        RETURN o.titulo AS titulo,
               o.modalidad AS modalidad,
               o.seniority_buscado AS seniority_buscado,
               o.salario_max_usd AS salario,
               o.fecha_publicacion AS fecha_publicacion,
               o.meses_min_experiencia AS meses_min_experiencia,
               o.mult_tecnico AS w_tec,
               o.mult_blando AS w_blan,
               o.mult_experiencia AS w_exp,
               collect({nombre: h.nombre, nivel_minimo: r.nivel_minimo, es_critica: r.es_critica, tipo: h.tipo}) AS requisitos
        """
        result = self.run_query(query, {"titulo": titulo})
        return result[0] if result else None
    
    def get_all_skills(self):
        query = "MATCH (h:Habilidad) RETURN h.nombre AS nombre, h.tipo AS tipo ORDER BY nombre"
        return self.run_query(query)

    def get_all_companies(self):
        query = "MATCH (e:Empresa) RETURN e.nombre AS nombre, e.email AS email, e.sitio_web AS sitio_web, e.rubro AS rubro ORDER BY nombre"
        return self.run_query(query)

    def company_exists(self, email):
        query = "MATCH (e:Empresa {email: $email}) RETURN count(e) > 0 AS existe"
        result = self.run_query(query, {"email": email})
        return result[0]['existe'] if result else False

    def get_best_candidates_for_offer(self, oferta_titulo, limit=5):
        query = """
            MATCH (c:Candidato)-[a:ADECUACION]->(o:Oferta {titulo: $titulo})
            RETURN c.nombre + ' ' + c.apellido AS nombre, a.score_final AS score
            ORDER BY a.score_final DESC LIMIT $limit
        """
        return self.run_query(query, {"titulo": oferta_titulo, "limit": limit})


    # --- CREAR ENTIDADES ---
    def create_candidate(self, datos_personales, email, perfil):
        query = """
            CREATE (c:Candidato {
                nombre: $personales.nombre, 
                apellido: $personales.apellido, 
                email: $email, 
                ubicacion: $personales.ubicacion, 
                fecha_nacimiento: date($personales.fecha_nac),
                seniority: $perfil.seniority, 
                movilidad: $perfil.movilidad
            })
        """
        params = {
            "personales": datos_personales,
            "email": email,
            "perfil": perfil
        }
        return self.run_query(query, params)

    def create_skill(self, nombre, tipo):
        query= """
            CREATE (:Habilidad {
                nombre: $nombre,
                tipo: $tipo
            })
        """
        params = {
            "nombre": nombre,
            "tipo": tipo
        }
        self.run_query(query, params)

    def create_offer(self, titulo, detalles, mults, email_empresa):
        #TODO: ver si agrego: meses_min_experiencia: toInteger($detalles.meses_min_experiencia),
        query= """
            MATCH (e:Empresa {email: $email_empresa})
            CREATE (o:Oferta {
                titulo: $titulo,
                descripcion: $detalles.descripcion, 
                modalidad: $detalles.modalidad, 
                seniority_buscado: $detalles.seniority_buscado, 
                salario_max_usd: $detalles.salario_max_usd,
                meses_min_experiencia: toInteger($detalles.meses_min_experiencia),
                fecha_publicacion: date(),
                mult_tecnico: toFloat($mults.tecnico),
                mult_blando: toFloat($mults.blando),
                mult_experiencia: toFloat($mults.experiencia)
            })
            MERGE (e)-[:PUBLICA {fecha_inicio: date()}]->(o)
            RETURN o.titulo AS oferta_creada
        """
        params = {
            "titulo": titulo,
            "email_empresa": email_empresa,
            "detalles": detalles,
            "mults": mults
        }
        self.run_query(query, params)


    def create_company(self, email, datos_empresa):
        query= """
            CREATE (:Empresa {
                nombre: $datos.nombre, 
                rubro: $datos.rubro, 
                sitio_web: $datos.sitio_web, 
                email: $email
                })
        """
        params = {
            "email": email,
            "datos": datos_empresa
        }
        self.run_query(query, params)


    # --- CREAR ALGUNAS RELACIONES ---
    def add_skill_to_candidate(self, email, nombre_habilidad, nivel):
        # Candidato - POSEE -> Habilidad
        query = """
            MATCH (c:Candidato {email: $email})
            MATCH (h:Habilidad {nombre: $nombre_habilidad})
            MERGE (c)-[p:POSEE]->(h)
                SET p.nivel = $nivel, 
                p.ultimo_uso = date()
        """
        self.run_query(query, {"email": email, "nombre_habilidad": nombre_habilidad, "nivel": nivel})

    def add_experience_to_candidate(self, email_candidato, email_empresa, experiencia):
        #Candidato - TRABAJO_EN -> Empresa
        query = """
            MATCH (c:Candidato {email: $email_candidato})
            MATCH (e:Empresa {email: $email_empresa})
            MERGE (c)-[t:TRABAJO_EN {puesto: $experiencia.puesto}]->(e)
            SET t.fecha_inicio = date($experiencia.fecha_inicio), t.fecha_fin = date($experiencia.fecha_fin)
        """
        params = {
            "email_candidato": email_candidato,
            "email_empresa": email_empresa,
            "experiencia": experiencia
        }
        return self.run_query(query, params)

    def add_requirement_to_offer(self, oferta_titulo, habilidad_nombre, nivel_min, es_critica):
        # Oferta - REQUIERE -> Habilidad
        query = """
            MATCH (o:Oferta {titulo: $oferta_titulo})
            MATCH (h:Habilidad {nombre: $habilidad_nombre})
            MERGE (o)-[r:REQUIERE]->(h)
            SET r.nivel_minimo = $nivel_min, r.es_critica = $es_critica
        """
        return self.run_query(query, {
            "oferta_titulo": oferta_titulo, 
            "habilidad_nombre": habilidad_nombre, 
            "nivel_min": nivel_min, 
            "es_critica": es_critica
        })
    
    # --- GUARDAR ADECUACION (Persistir el Score) ---
    def save_matching_score(self, email, oferta_titulo, scores):
        query = """
            MATCH (c:Candidato {email: $email})
            MATCH (o:Oferta {titulo: $oferta_titulo})
            MERGE (c)-[a:ADECUACION]->(o)
            SET a.score_final = $scores.final,
                a.score_tecnico = $scores.tecnico,
                a.score_blando = $scores.blando,
                a.score_experiencia = $scores.exp,
                a.fecha_calculo = datetime()
        """
        params = {"email": email, "oferta_titulo": oferta_titulo, "scores": scores}
        self.run_query(query, params)



#TODO: crear una funcion para actualizar una oferta