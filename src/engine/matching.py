from datetime import date
from dateutil.relativedelta import relativedelta


class MatchingEngine:
    def __init__(self):
        pass

    
    # Calculo de meses
    @staticmethod
    def months_between(start, end):
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
        
        if not soft_reqs:
            return 1.0
        
        for req in offer_requirements:
            skill_cand = candidate_skills.get(req["nombre"])
            
            if not skill_cand:
                scores.append(0)
                continue

            cand_level = skill_cand['nivel']
            req_level = req['nivel_min']

            scores.append(min(cand_level / req_level, 1))

        return sum(scores) / len(scores) if scores else 0
    

    # ------ CALCULO DEL SCORE EXPERIENCIA -------
    def calculate_experience_score(self, candidate_experience, offer_requirements):
        total_months = 0

        
        return 
    

    # -------- CALCULO DEL SCORE FINAL ------
    def calculate_total_score(self, candidate_data, offer_data):
        tech_score = offer_data['w_tec'] * self.calculate_technical_score(candidate_data['habilidades'], offer_data['requisitos'])
        soft_score = offer_data['w_blan'] * self.calculate_soft_score(candidate_data['habilidades'], offer_data['requisitos'])
        exp_score = offer_data['w_exp'] * self.calculate_experience_score(candidate_data['experiencias'], offer_data['seniority_buscado'])
        
        final_score = (tech_score + soft_score + exp_score)
        return {
            "final_score": round(final_score, 2),
            "tech_score": round(tech_score, 2),
            "soft_score": round(soft_score, 2),
            "exp_score": round(exp_score, 2)
        }
    