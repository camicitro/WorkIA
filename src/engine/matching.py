from datetime import date
from dateutil.relativedelta import relativedelta
from sentence_transformers import SentenceTransformer, util

ROLE_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


class MatchingEngine:

    EXPERIENCE_AFFINITY_THRESHOLD = 0.6

    def __init__(self):
        pass

    
    # Calculo de meses
    @staticmethod
    def months_between(start, end):
        # Función auxiliar para convertir fechas de Neo4j a Python
        def to_python_date(d):
            if d is None:
                return None
            # Si tiene el método to_native (caso de objetos Neo4j), lo usamos
            if hasattr(d, "to_native"):
                return d.to_native()
            return d

        # Convertimos ambos parámetros
        start = to_python_date(start)
        end = to_python_date(end)
        
        if not start:
            return 0
        if not end:
            end = date.today()
        delta = relativedelta(end, start)
        return delta.years * 12 + delta.months

    # Calculo del peso del uso de habilidad
    @staticmethod
    def recency_factor(ultimo_uso):
        if not ultimo_uso:
            return 0.5

        months = MatchingEngine.months_between(ultimo_uso, date.today())

        if months <= 6:
            return 1.0
        elif months <= 12:
            return 0.8
        elif months <= 24:
            return 0.6
        else:
            return 0.4

    
    # ------- CALCULO DE SCORE TECNICO -------
    def calculate_technical_score(self, candidate_skills, offer_requirements):
        total_score = 0
        total_weight = 0

        tech_reqs = [r for r in offer_requirements if r['tipo'] == 'Técnica']
        
        if not tech_reqs:
            return 1.0
        
        tech_skills_cand = {
            h["nombre"]: h for h in candidate_skills if h["tipo"] == "Técnica"
        }
        
        for req in tech_reqs:
            min_req_level = req['nivel_minimo']
            critical = req['es_critica']

            w_crit = 1.5 if critical else 1.0
            total_weight += w_crit

            skill_cand = tech_skills_cand.get(req['nombre'])

            if not skill_cand:
                continue


            cand_level = skill_cand['nivel']
            last_used = skill_cand['ultimo_uso']

            level_match = min(cand_level / min_req_level, 1)
            recency = MatchingEngine.recency_factor(last_used)

            total_score += level_match * recency * w_crit

        return total_score / total_weight if total_weight > 0 else 0
    

    # ------- CALCULO DEL SCORE BLANDO -----
    def calculate_soft_score(self, candidate_skills, offer_requirements):
        scores = []
        soft_reqs = [r for r in offer_requirements if r['tipo'] == 'Blanda']
        
        cand_skills_dict = {h["nombre"]: h for h in candidate_skills if h["tipo"] == "Blanda"}
        
        if not soft_reqs:
            return 1.0
        
        for req in soft_reqs:
            skill_cand = cand_skills_dict.get(req["nombre"])
            
            if not skill_cand:
                scores.append(0)
                continue

            cand_level = skill_cand['nivel']
            req_level = req['nivel_minimo']

            scores.append(min(cand_level / req_level, 1))

        return sum(scores) / len(scores) if scores else 0
    

    # ------ CALCULO DEL SCORE EXPERIENCIA -------
    def role_affinity(self, candidate_role, offer_role):
        emb_cand = ROLE_MODEL.encode(candidate_role, convert_to_tensor=True)
        emb_offer = ROLE_MODEL.encode(offer_role, convert_to_tensor=True)

        similarity = util.cos_sim(emb_cand, emb_offer).item()

        # se podria mejorar usando cacje de embeddings, evitando recalcular, VER para despues

        return max(0.0, min(float(similarity), 1.0)) # entre 0 y 1


    def calculate_experience_score(self, candidate_experiences, offer_title, min_required_months):
        if min_required_months <= 0:
            return 1.0
        if not candidate_experiences:
            return 0.0
        
        total_weighted_months = 0.0

        for exp in candidate_experiences:
            role_exp = exp['puesto']
            start = exp['fecha_inicio']
            end = exp['fecha_fin']

            months = MatchingEngine.months_between(start, end)
            if months <= 0: # no cuenta si es menos de un mes (por ej 25 dias)
                continue

            affinity = self.role_affinity(role_exp, offer_title)
            
            if affinity >= self.EXPERIENCE_AFFINITY_THRESHOLD:
                total_weighted_months += months * affinity  # podria simplemente sumar los meses pero quiero que cuente la afinidad, aunque podria penalizar roles muy similares pero no iguales

        score = total_weighted_months / min_required_months

        return min(score, 1.0)
    

    # -------- CALCULO DEL SCORE FINAL ------
    def calculate_total_score(self, candidate_data, offer_data):
        tech_score = self.calculate_technical_score(candidate_data['habilidades'], offer_data['requisitos'])
        soft_score = self.calculate_soft_score(candidate_data['habilidades'], offer_data['requisitos'])
        exp_score = self.calculate_experience_score(candidate_data['experiencias'], offer_data['titulo'], offer_data['meses_min_experiencia'])
        
        final_score = (offer_data['w_tec'] * tech_score + offer_data['w_blan'] * soft_score + offer_data['w_exp'] * exp_score)
        return {
            "final_score": round(final_score, 2),
            "tech_score": round(tech_score, 2),
            "soft_score": round(soft_score, 2),
            "exp_score": round(exp_score, 2)
        }
    