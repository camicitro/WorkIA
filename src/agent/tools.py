from langchain.tools import tool
from src.database.neo4j_service import Neo4jService
from src.engine.matching import MatchingEngine

db = Neo4jService()
engine = MatchingEngine()

@tool
def search_candidates(criteria: str):
    """
    Busca candidatos en la base de datos por nombre o apellido. 
    Es útil para encontrar el email de un candidato si solo se conoce su nombre.
    """
    return db.get_all_candidates(criteria)

@tool
def search_offers(title: str, date_from: str, date_to: str):
    """
    Busca ofertas laborales por título en un rango de fechas específico.
    'date_from' y 'date_to' deben estar en formato 'YYYY-MM-DD'.
    """
    return db.get_all_offers(title, date_from, date_to)

@tool
def analyze_candidate_suitability(email: str, offer_title: str):
    """
    Calcula la adecuación entre un candidato (email) y una oferta (título).
    Genera puntajes técnicos, de habilidades blandas y de experiencia,
    y guarda el resultado en la base de datos.
    """
    try:
        candidate = db.get_candidate_profile(email)
        offer = db.get_offer_requirements(offer_title)

        if not candidate or not offer:
            return "No se encontró el candidato o la oferta especificada"
        
        result = engine.calculate_total_score(candidate, offer)

        db.save_matching_score(email, offer['titulo'], {
            "final": result['final_score'],
            "tecnico": result['tech_score'],
            "blando": result['soft_score'],
            "exp": result['exp_score']
        })

        return {
            "message": "Análisis completado y guardado exitosamente",
            "candidate": candidate['nombre_completo'],
            "offer": offer['titulo'],
            "scores_details": result
        }
    except Exception as e:
        return f"Error al procesar la adecuación {str(e)}"
    

@tool
def get_complete_profile(email: str):
    """
    Obtiene el perfil detallado de un candidato, incluyendo todas sus 
    habilidades registradas y su historial de experiencias laborales.
    """
    return db.get_candidate_profile(email)

@tool
def list_available_skills():
    """
    Devuelve una lista de todas las habilidades (técnicas y blandas) 
    que existen actualmente en el sistema.
    """
    return db.get_all_skills()

@tool
def save_complete_candidate(personal_data: dict, skills: list, experiences: list):
    """
    Registra un nuevo candidato completo con sus habilidades y experiencias.
    'personal_data' debe incluir: nombre, apellido, email, ubicacion, fecha_nacimiento, seniority, movilidad.
    'skills': lista de {'nombre': str, 'nivel': int}.
    'experiences': lista de {'empresa_email': str, 'puesto': str, 'fecha_inicio': str, 'fecha_fin': str}.
    """
    try:
        db.create_candidate(
            datos_personales = personal_data, 
            email = personal_data['email'], 
            perfil = personal_data)
        for s in skills:
            db.add_skill_to_candidate(
                email = personal_data['email'], 
                nombre_habilidad = s['nombre'], 
                nivel = s['nivel']
            )

        for e in experiences:
            db.add_experience_to_candidate(
                email_candidato = personal_data['email'], 
                email_empresa = e['empresa_email'], 
                experiencia = e
            )

        return f"Candidato {personal_data['nombre']} guardado exitosamente"
    except Exception as e:
        return f"Error al guardar candidato: {str(e)}"
    
@tool
def save_offer(title: str, company_email: str, offer_details: dict, weighters: dict, skills_required: list):
    """
    Crea una nueva oferta laboral vinculada a una empresa y define sus requisitos.
    'offer_details': {descripcion, modalidad, seniority_buscado, salario_max_usd, meses_min_experiencia}.
    'weighters': {tecnico: float, blando: float, experiencia: float}.
    'skills_required': lista de {'habilidad': str, 'nivel_minimo': int, 'es_critica': bool}.
    """
    try:
        if not db.company_exists(company_email):
            return f"Error al guardar oferta. No se encontró una empresa con el mail {company_email}"
        
        db.create_offer(
            titulo=title, 
            detalles=offer_details, 
            mults=weighters, 
            email_empresa=company_email
        )
       
        for s in skills_required:
            db.add_requirement_to_offer(
                oferta_titulo=title, 
                habilidad_nombre = s['habilidad'], 
                nivel_min = s['nivel_minimo'],
                es_critica = s['es_critica'])

        return f"Oferta {title} guardada exitosamente"
    
    except Exception as e:
        return f"Error al guardar oferta: {str(e)}"