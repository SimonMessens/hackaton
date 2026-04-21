Confidential Synthetis
Workshop IA - Vibe Coding Challenge
Développer un assistant d'encodage actiTime en local, avec du code généré à 99 % par IA.
Pendant 2 heures, l'objectif est de construire un petit assistant en terminal qui prend une description libre de la
journée de l'utilisateur, retrouve les tâches actiTime pertinentes, génère un fichier Excel à vérifier, puis permet
de mettre actiTime à jour à partir de ce fichier. Le but n'est pas de produire du code parfait, mais d'apprendre à
piloter l'IA efficacement.
1. PRÉREQUIS
• Installer VS Code ou Visual Studio.
• Avoir un compte GitHub Synthetis fonctionnel.
• Pouvoir utiliser GitHub Copilot Chat ; idéalement avec accès aux modèles premium via le compte
Synthetis.
• Pouvoir se connecter à actiTime.
• Choisir un langage capable d'appeler l'API actiTime et d'utiliser GitHub Copilot SDK:
JavaScript/TypeScript, Python, C#, Java, Go, etc.
2. RÈGLES DU CHALLENGE
• Durée : 2 heures.
• Le projet doit tourner en local.
• Le code doit être généré à 99 % par IA. Vous êtes le pilote, pas le scribe.
• Pas d'interface graphique attendue ; une version terminal / CLI suffit largement.
• L'objectif est un POC fonctionnel de bout en bout, pas un projet propre ou industrialisé.
3. FONCTIONNALITÉS ATTENDUES
• L'assistant demande à l'utilisateur de saisir ses identifiants au démarrage via le CLI (pas de fichier
  .env, pas de valeurs codées en dur) :
    - actiTime username
    - actiTime password (saisie masquée)
    - GitHub PAT (pour les appels LLM via GitHub Models, saisie masquée)
  Ces valeurs sont conservées en mémoire le temps de la session uniquement.
• L'assistant permet à l'utilisateur de s'authentifier à actiTime.
• L'utilisateur peut saisir, pour une journée choisie, ce qu'il a fait en langage naturel.
• L'assistant récupère les tâches actiTime pertinentes de l'utilisateur sur le mois en cours.
• L'assistant appelle un LLM (e.g. GitHub Copilot SDK) pour déduire à quelles tâches actiTime
correspondent les activités décrites.
• Le LLM doit idéalement renvoyer une structure exploitable, par exemple du JSON.
• L'assistant vérifie le format et la cohérence des données renvoyées.
• L'assistant génère un nouveau fichier Excel avec les temps déjà présents sur actiTime et les nouvelles
données proposées.
• Après validation humaine de l'Excel, l'assistant permet de mettre actiTime à jour à partir de ce fichier.
Confidential Synthetis
4. TIPS
a. VÉRIFICATIONS MINIMALES À PRÉVOIR
• Le format de sortie du LLM est valide et exploitable.
• Chaque activité est reliée à une tâche actiTime existante.
• Les durées sont cohérentes pour la journée encodée.
• Le total hebdomadaire reste cohérent avec le régime de travail de l'utilisateur ; pour la plupart des
participants, la référence est de 39 heures par semaine.
b. ÉTAPES SUGGÉRÉES
• Créer un projet minimal et demander à Copilot de proposer une structure simple.
• Faire une première connexion à l'API actiTime et récupérer quelques données utiles.
• Concevoir le prompt et tester l'appel au LLM séparément.
• Ajouter une étape de validation des données renvoyées par le LLM.
• Générer l'Excel avec les données existantes + les nouvelles lignes proposées.
• Ajouter la confirmation utilisateur, puis l'envoi vers actiTime.
c. TRAVAILLER AVEC L'IA
• Dans VS Code, utilisez les modes Ask, Plan et Agent selon le besoin.
• Demandez d'abord un plan d’action, puis faites implémenter étape par étape.
• Quand quelque chose ne marche pas, redonnez le contexte, l'erreur exacte et le résultat attendu.
• Votre rôle reste celui d'architecte : vous décidez du périmètre, de l'ordre des étapes et de ce que vous
gardez ou non.
d. LIENS UTILES
• Swagger actiTime Synthetis : https://actitime.synthetis.com/api/v1/swagger
• Documentation API actiTime : https://www.actitime.com/api-documentation