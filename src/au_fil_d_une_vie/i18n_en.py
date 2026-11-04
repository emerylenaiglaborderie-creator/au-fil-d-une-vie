"""Catalogue anglais : phrase française (clé) -> traduction.

Les emplacements entre accolades ({name}, {count}...) doivent être identiques des deux
côtés : un test le vérifie, ainsi que l'absence de phrase non traduite.
"""

EN: dict[str, str] = {
    # Navigation, en-tête, pied de page
    "Ma quête": "My quest",
    "Interview": "Interview",
    "Récits": "Stories",
    "Graphe": "Graph",
    "Livre de famille": "Family book",
    "Paramètres": "Settings",
    "Réglages": "Settings",
    "Tout reste sur cet ordinateur. Rien n'est envoyé en ligne.": (
        "Everything stays on this computer. Nothing is sent online."
    ),
    "Installer": "Install",
    "Texte du récit en préparation": "Preparing the story's text",
    " · {count} en attente": " · {count} waiting",
    "Le texte du récit est prêt.": "The story's text is ready.",
    "Le texte d'un récit n'a pas pu être préparé.": "A story's text could not be prepared.",
    "Modèle de transcription non installé.": "Transcription model not installed.",
    "Un enregistrement est en cours. L'arrêter et l'effacer ?": (
        "A recording is in progress. Stop and delete it?"
    ),
    # Mots courants
    "Ajouter": "Add",
    "Enregistrer": "Save",
    "Modifier": "Edit",
    "Supprimer": "Delete",
    "Fermer": "Close",
    "Annuler": "Cancel",
    "Renommer": "Rename",
    "Aucun": "None",
    "Tout choisir": "Select all",
    "Tous": "All",
    "Plus tard": "Later",
    "Pause": "Pause",
    "Lecture": "Play",
    "Merci !": "Thank you!",
    "Bravo": "Well done",
    "Ce n'est pas réversible.": "This cannot be undone.",
    "C'est enregistré.": "Saved.",
    # Pluriels
    "récit": "story",
    "récits": "stories",
    "récit choisi": "story selected",
    "récits choisis": "stories selected",
    "récit recueilli": "story collected",
    "récits recueillis": "stories collected",
    "personne": "person",
    "personnes": "people",
    "proche": "relative",
    "proches": "relatives",
    "piste": "track",
    "pistes": "tracks",
    "question": "question",
    "questions": "questions",
    "lien": "link",
    "liens": "links",
    "aucun lien": "no link",
    "aucun récit": "no story",
    "pas encore de récit": "no story yet",
    "{done} sur {total}": "{done} of {total}",
    # Bienvenue
    "Ta quête commence": "Your quest begins",
    "Bienvenue": "Welcome",
    "Au fil d'une vie t'aide à recueillir les souvenirs de ta famille : tu poses une question à un proche, tu enregistres sa réponse, et les récits se relient entre eux au fil des mots.": (
        "Au fil d'une vie helps you gather your family's memories: you ask a relative a "
        "question, record the answer, and the stories link together through their words."
    ),
    "Comment t'appelles-tu ?": "What's your name?",
    "Ton prénom": "Your first name",
    "Quel âge as-tu ?": "How old are you?",
    "15 ans ou plus": "15 or older",
    "Moins de 15 ans": "Under 15",
    "Pour ton parent": "For your parent",
    "Votre enfant va enregistrer la voix de proches qui acceptent de raconter leurs souvenirs. Tout reste sur cet ordinateur : pas de compte, rien n'est envoyé en ligne. Chaque proche donne son accord avant chaque enregistrement, et chaque récit peut être masqué ou supprimé à tout moment.": (
        "Your child will record the voices of relatives who agree to share their memories. "
        "Everything stays on this computer: no account, nothing is sent online. Each "
        "relative gives their consent before every recording, and any story can be hidden "
        "or deleted at any time."
    ),
    "Je suis le parent ou le responsable légal, j'ai lu ce qui précède et je suis d'accord pour que mon enfant utilise Au fil d'une vie.": (
        "I am the parent or legal guardian, I have read the above and I agree to my child "
        "using Au fil d'une vie."
    ),
    "Qui vas-tu interroger ?": "Who will you interview?",
    "Ajoute quelques proches maintenant, ou plus tard depuis ta quête.": (
        "Add a few relatives now, or later from your quest."
    ),
    "Commencer ma quête": "Start my quest",
    # Ma quête
    "Bonjour": "Hello",
    "Bonjour {name}": "Hello {name}",
    "Ton enquête avance. Voici la prochaine piste à suivre.": (
        "Your search is moving forward. Here is the next track to follow."
    ),
    "Ta quête commence ici. Choisis une piste et pose ta première question.": (
        "Your quest starts here. Pick a track and ask your first question."
    ),
    "Prochaine piste": "Next track",
    "À poser à": "Ask",
    "Ajoute d'abord un proche à interroger": "First add a relative to interview",
    "Ajoute d'abord un proche à interroger.": "First add a relative to interview.",
    "Lancer l'interview": "Start the interview",
    "Une autre piste": "Another track",
    "Prévois une dizaine de minutes, un endroit calme et l'accord de la personne.": (
        "Plan about ten minutes, a quiet place and the person's consent."
    ),
    "Toutes les pistes ont été explorées.": "Every track has been explored.",
    "Les pistes à explorer": "Tracks to explore",
    "Modifier les pistes et les questions": "Edit tracks and questions",
    "À commencer": "Not started",
    "ton arbre pousse": "your tree is growing",
    "{stories} auprès de {people}": "{stories} from {people}",
    "Les personnes à interroger": "People to interview",
    "+ Ajouter ou modifier un proche": "+ Add or edit a relative",
    "Pas encore de récit": "No story yet",
    # Interview
    "{track} · Piste en cours": "{track} · Current track",
    "Pose-lui la question...": "Ask the question...",
    "Tu interroges": "You're interviewing",
    "Changer de question": "Change question",
    "Ajouter un proche": "Add a relative",
    "Commencer l'enregistrement": "Start recording",
    "Reprendre": "Resume",
    "Terminer": "Finish",
    "Recommencer": "Start over",
    "Prêt": "Ready",
    "En cours": "Recording",
    "En pause": "Paused",
    "Nouvelle interview": "New interview",
    "Retour à ma quête": "Back to my quest",
    "À la fin, le texte du récit est préparé sur cet ordinateur. Tu pourras ensuite le relire et le corriger avant de l'ajouter à tes récits.": (
        "Afterwards, the story's text is prepared on this computer. You can then read it "
        "and correct it before adding it to your stories."
    ),
    "Pour creuser": "To dig deeper",
    "Conseils d'écoute": "Listening tips",
    "Laisse des silences : souvent, la personne continue.": (
        "Leave some silences: people often keep going."
    ),
    "Écoute avant de corriger ou de compléter.": "Listen before correcting or adding.",
    "Pose une seule question à la fois.": "Ask one question at a time.",
    "D'autres pistes": "Other tracks",
    "Tu te souviens d'un détail précis ?": "Do you remember a specific detail?",
    "Qui était là avec toi ?": "Who was there with you?",
    "Qu'est-ce que tu ressentais à ce moment-là ?": "How did you feel at that moment?",
    "Le récit de {name} ({duration}) est gardé sur cet ordinateur. Son texte se prépare ici même, sans rien envoyer en ligne : tu peux suivre l'avancement en bas de la fenêtre.": (
        "{name}'s story ({duration}) is kept on this computer. Its text is being prepared "
        "right here, without sending anything online: you can follow the progress at the "
        "bottom of the window."
    ),
    "Effacer cet enregistrement et recommencer ?": "Delete this recording and start over?",
    "Coche l'accord de la personne pour commencer.": "Tick the person's consent to start.",
    "Onde sonore de l'enregistrement, tracée comme un fil": (
        "Sound wave of the recording, drawn as a thread"
    ),
    "{name} sait que la conversation est enregistrée et est d'accord pour que son récit soit gardé dans l'application.": (
        "{name} knows the conversation is being recorded and agrees to their story being "
        "kept in the app."
    ),
    # Enregistrement et micro
    "Un enregistrement est déjà en cours.": "A recording is already in progress.",
    "Le consentement du proche est obligatoire.": "The relative's consent is required.",
    "Aucun enregistrement en cours.": "No recording in progress.",
    "L'enregistrement est trop court.": "The recording is too short.",
    "Aucun micro n'a été trouvé. ": "No microphone was found. ",
    "Le micro n'a pas pu démarrer. ": "The microphone could not start. ",
    "Le format du micro n'est pas pris en charge.": "The microphone's format is not supported.",
    "Vérifie qu'un micro est branché et que l'application a le droit de l'utiliser (sur Mac : Réglages Système, Confidentialité et sécurité, Micro).": (
        "Check that a microphone is plugged in and that the app is allowed to use it (on "
        "Mac: System Settings, Privacy & Security, Microphone)."
    ),
    # Mes récits
    "Récits recueillis": "Collected stories",
    "Mes récits": "My stories",
    "Du plus récent au plus ancien, tout ce que ta famille t'a raconté.": (
        "From newest to oldest, everything your family has told you."
    ),
    "Un mot, une personne, un lieu": "A word, a person, a place",
    "Aucun récit ne correspond à ta recherche.": "No story matches your search.",
    "Pas encore de récit. Lance ta première interview : il apparaîtra ici.": (
        "No story yet. Start your first interview: it will appear here."
    ),
    " · masqué": " · hidden",
    "Le texte de ce récit est en préparation…": "This story's text is being prepared…",
    "Le texte de ce récit n'est pas encore prêt.": "This story's text is not ready yet.",
    # Fiche récit
    "←  Récits": "←  Stories",
    "{name} raconte": "{name} remembers",
    "Version livre": "Book version",
    "Transcription brute": "Raw transcript",
    "Corriger le texte": "Edit the text",
    "Corriger la transcription": "Correct the transcript",
    "Texte du récit à corriger": "Story text to correct",
    "Enregistrer la correction": "Save the correction",
    "Corrige ce qui a été mal compris : un mot mal entendu, un nom mal écrit. Tu peux réécouter le passage avec le lecteur au-dessus.": (
        "Correct what was misunderstood: a misheard word, a misspelled name. You can "
        "listen to the passage again with the player above."
    ),
    " La version livre, déjà corrigée, ne change pas.": (
        " The book version, already edited, does not change."
    ),
    "Version pour le livre de famille : tu peux aussi reformuler. La transcription brute est gardée à côté.": (
        "Version for the family book: you can also rephrase. The raw transcript is kept alongside."
    ),
    "Le texte ne peut pas être vide.": "The text cannot be empty.",
    "Le texte de ce récit est en préparation, sur cet ordinateur…": (
        "This story's text is being prepared, on this computer…"
    ),
    "Le texte de ce récit n'est pas encore prêt. Il sera préparé dès que le modèle de transcription sera installé.": (
        "This story's text is not ready yet. It will be prepared as soon as the "
        "transcription model is installed."
    ),
    "Mots-clés": "Keywords",
    "+ ajouter": "+ add",
    "Un mot à ajouter": "A word to add",
    "Une feuille pleine est un mot qu'on retrouve dans un autre récit.": (
        "A filled leaf is a word found in another story too."
    ),
    "Mots proposés": "Suggested words",
    "Clique sur un mot pour le garder, sur × pour l'écarter.": (
        "Click a word to keep it, × to dismiss it."
    ),
    "Garder ce mot": "Keep this word",
    "Retirer ce mot": "Remove this word",
    "Retirer {word}": "Remove {word}",
    "Voir aussi": "See also",
    "Pas encore de lien avec un autre récit.": "No link with another story yet.",
    "Mon carnet": "My notebook",
    "Ce que j'en retiens": "What I take from it",
    "Une phrase, un détail, une question pour la prochaine fois...": (
        "A sentence, a detail, a question for next time..."
    ),
    "Gardé dans ton carnet.": "Kept in your notebook.",
    "Ajouter au livre de famille": "Add to the family book",
    "Retirer du livre de famille": "Remove from the family book",
    "Un récit entre dans le livre quand son texte est prêt et visible.": (
        "A story can go into the book once its text is ready and visible."
    ),
    "Masquer ce récit": "Hide this story",
    "Ne plus masquer": "Unhide",
    "Supprimer ce récit ? L'enregistrement, son texte, ses mots-clés et ta note seront effacés de cet ordinateur. Ce n'est pas réversible.": (
        "Delete this story? The recording, its text, its keywords and your note will be "
        "erased from this computer. This cannot be undone."
    ),
    "Pas d'enregistrement pour ce récit.": "No recording for this story.",
    "Vitesse de lecture": "Playback speed",
    "Le texte est vide.": "The text is empty.",
    "Le mot-clé est vide.": "The keyword is empty.",
    # Graphe
    "Graphe des liens": "Link graph",
    "Au fil des mots": "Through the words",
    "Afficher les mots communs": "Show shared words",
    "Graphe des liens entre les récits": "Graph of the links between stories",
    "pas encore de lien": "no link yet",
    "Le graphe apparaîtra quand tu auras recueilli et relié quelques récits.": (
        "The graph will appear once you have collected and linked a few stories."
    ),
    "{stories} récits, {linked} reliés par {words} mots communs. Double-clique sur un récit pour l'ouvrir.": (
        "{stories} stories, {linked} linked by {words} shared words. Double-click a story "
        "to open it."
    ),
    "Récit sélectionné": "Selected story",
    "Pas encore de mot en commun avec un autre récit.": "No word in common with another story yet.",
    "Ouvrir la fiche": "Open the story",
    "Légende": "Legend",
    "Un récit": "A story",
    "Un récit sans lien pour l'instant": "A story with no link yet",
    "Un mot qu'on retrouve ailleurs": "A word found elsewhere",
    "Un fil entre un récit et un mot": "A thread between a story and a word",
    # Livre de famille
    "Le livre de famille": "The family book",
    "Choisis les récits à mettre dans ton livre. Il est créé en PDF sur cet ordinateur, avec un sommaire, les liens entre les récits et un index des mots.": (
        "Choose the stories to put in your book. It is created as a PDF on this computer, "
        "with a table of contents, the links between stories and an index of words."
    ),
    "Aucun récit n'a encore son texte. Enregistre une interview : elle pourra entrer dans le livre une fois transcrite.": (
        "No story has its text yet. Record an interview: it can go into the book once transcribed."
    ),
    "Mise en page du livre...": "Laying out the book...",
    "Ton livre est prêt.": "Your book is ready.",
    "Ouvrir le livre": "Open the book",
    "Afficher le dossier": "Show the folder",
    "Créer le PDF": "Create the PDF",
    "Enregistrer le livre": "Save the book",
    "Livre de famille.pdf": "Family book.pdf",
    "Le livre n'a pas pu être créé. ({message})": "The book could not be created. ({message})",
    "recueilli par {name}": "collected by {name}",
    "Sommaire": "Contents",
    "Piste": "Track",
    "Mots : {words}": "Words: {words}",
    "Index des mots": "Index of words",
    "Aucun récit n'a encore été ajouté au livre. Choisis-en dans l'application, puis crée le livre à nouveau.": (
        "No story has been added to the book yet. Choose some in the app, then create the "
        "book again."
    ),
    # Modèle de transcription
    "Une dernière étape": "One last step",
    "Pour transformer tes enregistrements en texte, l'application a besoin d'un modèle de reconnaissance de la voix (environ {mb} Mo).": (
        "To turn your recordings into text, the app needs a speech recognition model "
        "(about {mb} MB)."
    ),
    "Il est téléchargé une seule fois. C'est le seul moment où l'application utilise internet : ensuite, tout se fait sur cet ordinateur, même sans connexion.": (
        "It is downloaded only once. This is the only time the app uses the internet: "
        "afterwards, everything happens on this computer, even offline."
    ),
    "Téléchargement en cours...": "Downloading...",
    "Télécharger le modèle": "Download the model",
    "Sans ce modèle, tu peux quand même enregistrer : les textes seront préparés dès qu'il sera installé.": (
        "Without this model you can still record: texts will be prepared as soon as it is "
        "installed."
    ),
    "Le téléchargement n'a pas abouti. Vérifie ta connexion et réessaie. ({message})": (
        "The download did not complete. Check your connection and try again. ({message})"
    ),
    # Proches
    "Mes proches": "My relatives",
    "Personne pour l'instant.": "Nobody yet.",
    "Modifier {name}": "Edit {name}",
    "Supprimer {name} ?": "Delete {name}?",
    " Son récit et son enregistrement seront aussi effacés.": (
        " Their story and its recording will be erased too."
    ),
    " Ses {count} récits et leurs enregistrements seront aussi effacés.": (
        " Their {count} stories and recordings will be erased too."
    ),
    "Comment tu l'appelles (Mamie Jeanne, Papa...)": "What you call them (Grandma Jane, Dad...)",
    "Lien avec toi": "Relationship to you",
    "Indique comment tu appelles cette personne.": "Say what you call this person.",
    "Ce nom est trop long.": "This name is too long.",
    "« {name} » est déjà dans tes proches.": "“{name}” is already one of your relatives.",
    # Paramètres
    "Mon profil": "My profile",
    "Moins de 15 ans, avec l'accord d'un parent.": "Under 15, with a parent's consent.",
    "15 ans ou plus.": "15 or older.",
    "Apparence": "Appearance",
    "Langue": "Language",
    "Change la langue de l'application et de la transcription. Tes récits et tes pistes gardent la langue dans laquelle tu les as écrits.": (
        "Changes the language of the app and of the transcription. Your stories and tracks "
        "keep the language you wrote them in."
    ),
    "Thème": "Theme",
    "Comme l'ordinateur": "Like the computer",
    "Jour": "Day",
    "Nuit": "Night",
    "« Comme l'ordinateur » suit le mode clair ou sombre de ton système.": (
        "“Like the computer” follows your system's light or dark mode."
    ),
    "Ajouter, modifier ou supprimer un proche": "Add, edit or delete a relative",
    "{people} dans ta quête.": "{people} in your quest.",
    "Pistes et questions": "Tracks and questions",
    "Créer, renommer ou réordonner les pistes": "Create, rename or reorder tracks",
    "{tracks}, {questions}.": "{tracks}, {questions}.",
    "Mes données": "My data",
    "Tout est rangé sur cet ordinateur, dans ce dossier. Rien n'est envoyé en ligne.": (
        "Everything is stored on this computer, in this folder. Nothing is sent online."
    ),
    "Ouvrir le dossier": "Open the folder",
    "Transcription": "Transcription",
    "Modèle « {size} » installé : les textes se préparent sur cet ordinateur.": (
        "“{size}” model installed: texts are prepared on this computer."
    ),
    "Le modèle n'est pas encore installé.": "The model is not installed yet.",
    "Installer le modèle": "Install the model",
    "Indique ton prénom.": "Enter your first name.",
    "Ce prénom est trop long.": "This first name is too long.",
    "Sous 15 ans, l'accord d'un parent est nécessaire.": "Under 15, a parent's consent is required.",
    "Aucun profil à modifier.": "No profile to edit.",
    # Pistes
    "Mes pistes": "My tracks",
    "Les pistes sont les thèmes de ta quête. Change-les comme tu veux : ajoute les tiennes, renomme-les, écris tes propres questions.": (
        "Tracks are the themes of your quest. Change them as you like: add your own, "
        "rename them, write your own questions."
    ),
    "Les pistes": "Tracks",
    "Nouvelle piste (Voyages, Sport...)": "New track (Travel, Sport...)",
    "Nom de la piste": "Track name",
    "Monter la piste": "Move track up",
    "Descendre la piste": "Move track down",
    "Ses questions": "Its questions",
    "Une nouvelle question à poser": "A new question to ask",
    "Supprimer cette piste": "Delete this track",
    "Crée une piste pour commencer.": "Create a track to begin.",
    "Elle a des récits : on peut la renommer, pas la supprimer.": (
        "It has stories: it can be renamed, not deleted."
    ),
    "Pas encore de récit dans cette piste.": "No story in this track yet.",
    "Pas encore de question.": "No question yet.",
    "Supprimer cette piste et ses questions ?": "Delete this track and its questions?",
    "Cette piste a déjà des récits : elle ne peut pas être supprimée. Tu peux la renommer.": (
        "This track already has stories: it cannot be deleted. You can rename it."
    ),
    "Cette question a déjà des récits : elle ne peut pas être supprimée. Tu peux corriger son texte.": (
        "This question already has stories: it cannot be deleted. You can correct its text."
    ),
    "Cette piste n'existe plus.": "This track no longer exists.",
    "Cette question n'existe plus.": "This question no longer exists.",
    "Donne un nom à la piste.": "Give the track a name.",
    "Ce nom de piste est trop long.": "This track name is too long.",
    "La piste « {name} » existe déjà.": "The track “{name}” already exists.",
    "Écris la question.": "Write the question.",
    "Cette question est trop longue.": "This question is too long.",
    "Cette question est déjà dans la piste.": "This question is already in the track.",
}
