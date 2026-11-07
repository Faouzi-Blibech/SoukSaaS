# Pitch SoukSaaS (TechX ENIT x ENICarthage)

Deck de 10 slides, environ 8 minutes avec la demo. Langue : francais, termes techniques en anglais.

## Slide 1 - Titre
- SoukSaaS : "The Autonomous FinTech Team"
- Une equipe d'agents IA qui vend, encaisse et analyse, en securite
- Equipe, ENIT x ENICarthage, TechX 14h

Note : une phrase d'accroche, puis annoncer le plan : probleme, solution, demo, securite, impact.

## Slide 2 - Probleme
- Les petits commercants vendent en ligne sans equipe commerciale, paiement ni data
- Les chatbots actuels sont vulnerables : prompt injection, fuite de donnees, remises inventees
- Confier un paiement a une IA sans controle est inacceptable
- Resultat : ventes perdues et confiance faible

Note : insister sur le couple opportunite / risque : l'autonomie n'a de valeur que si elle est controlee.

## Slide 3 - Solution
- Equipe de 6 agents coordonnes par un orchestrateur : vente, intelligence client, paiement, analyse, strategie, securite
- Parcours complet : question, reponse, paiement simule, KPIs, recommandations
- Le proprietaire valide le Q&A, approuve les paiements sensibles, envoie lui-meme les messages

Note : "autonome mais supervise". Aucun envoi ni paiement reel.

## Slide 4 - Plan de la demo (~3 min)
- 1. Page produit et Q&A valide (20 s)
- 2. Chat : 2 reponses Q&A, 1 fallback (30 s)
- 3. Injection bloquee, alerte visible (30 s)
- 4. Paiement `tok_success`, puis paiement suspect retenu et approuve (60 s)
- 5. Dashboard : KPIs, recommandations, brouillon d'outreach, badge audit OK (40 s)

Note : suivre le scenario du README ; si le reseau tombe, `LLM_MODE=mock` donne le meme deroulement.

## Slide 5 - Architecture multi-agent
- Voir le diagramme Mermaid dans `docs/ARCHITECTURE.md`
- Orchestrateur central ; chaque appel passe par le Security Gateway
- Etat partage SQLite + audit log chaine par hash
- Analytics en code deterministe ; le LLM n'ecrit qu'un resume optionnel

Note : choix volontaire de ne pas utiliser de framework d'agents lourd : simple, auditable, testable hors ligne.

## Slide 6 - Parcours FinTech
- Prospect interesse, puis plan choisi, puis paiement sandbox (tokens de test uniquement)
- Score de fraude explicable (montant, tentatives, refus, email jetable)
- Risque faible : execute ; moyen ou eleve : retenu pour approbation humaine
- Aucune donnee de carte : tout numero detecte (Luhn) est bloque et masque

Note : montrer qu'un paiement retenu n'est jamais execute sans clic du proprietaire.

## Slide 7 - Securite et confiance
- Couches : filtres deterministes, classifieur LLM (non fiable par defaut), matrice de permissions, filtrage des sorties, hygiene des prompts
- Moindre privilege : le Sales Agent ne peut pas appeler `payment.*`, Insights ne peut rien envoyer
- Audit log chaine par hash, verification d'integrite visible
- Human-in-the-loop : paiements retenus, escalades, brouillons
- Resultats des attaques : voir le dashboard (page Security, evals)

Note : citer les chiffres du dashboard au moment du pitch ; limites documentees dans `docs/SECURITY.md`.

## Slide 8 - Donnees et KPIs
- Donnees 100 % synthetiques (seed deterministe)
- KPIs deterministes : conversion, revenu, panier moyen, objections, entonnoir
- Bonus ML : prevision du revenu a 7 jours (tendance lineaire, R2 affiche)
- Recommandations appuyees sur des preuves (exemples cites)

Note : le LLM ne calcule jamais un chiffre ; il raconte des chiffres deja calcules.

## Slide 9 - Valeur et impact
- Une PME peut vendre 24h/24 sans equipe, avec une trace complete
- Confiance : chaque decision est expliquee et auditable
- Generalisable : tout produit decrit par un `product.json`
- Fonctionne hors ligne en mode mock ; mode live avec une cle LLM

Note : relier aux criteres : originalite (securite au centre), faisabilite, impact local (marche tunisien, FR/AR).

## Slide 10 - Limites, suite et equipe
- Limites : auth proprietaire simple, paiements simules, classifieur contournable, pas de revue INPDP
- Suite : voix temps reel, vrai PSP en sandbox, auth forte, modeles de fraude (IsolationForest), multi-produits
- Equipe : noms et roles
- Questions

Note : assumer les limites : c'est un signe de maturite securite.

## Pitch parle (1 minute)

Bonjour. Un commercant tunisien qui vend en ligne n'a ni equipe commerciale, ni service paiement, ni analyste.
Et s'il confie tout cela a une IA, il prend un risque : injection de prompt, fuite de donnees, paiement frauduleux.
SoukSaaS est une equipe d'agents IA autonomes mais supervisee. Un agent de vente repond aux prospects a partir d'un
Q&A valide par le proprietaire. Un agent de paiement execute des paiements simules, avec un score de fraude
explicable. Un agent d'analyse calcule les KPIs et une prevision de revenu. Un agent d'insights propose des
recommandations et des brouillons de relance que le proprietaire envoie lui-meme. Et au centre, un Security Gateway
filtre chaque message, applique le moindre privilege, et ecrit un journal d'audit chaine par hash. Tout paiement
sensible attend l'approbation humaine. Aucune carte, aucun envoi reel, donnees synthetiques. Nous allons vous le
montrer en direct : une injection bloquee, un paiement retenu, un dashboard qui se met a jour. Merci.
