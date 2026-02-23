# Αυτό το router υλοποιεί το Reset Demo. Η ουσία εδώ είναι ότι σβήνουμε μόνο rows με dataset="demo" 
# και μετά ξανατρέχουμε το seed_demo_data. Έτσι ο demo χρήστης μπορεί να κάνει αλλαγές 
# (π.χ. notes ή sessions) και να τις κρατάει μέχρι να πατήσει Reset. 
# Το πιο σημαντικό είναι ότι δεν υπάρχει περίπτωση να αγγίξει real δεδομένα, 
# γιατί το query φιλτράρει αποκλειστικά dataset="demo".

# """
# Deprecated / optional demo router.

# Το project αυτή τη στιγμή δεν χρησιμοποιεί dataset isolation (δεν υπάρχει πεδίο dataset στα models),
# οπότε το παλιό “Reset Demo” router δεν μπορεί να δουλέψει σωστά όπως ήταν.

# Αν θέλεις πραγματικό demo mode (οι αλλαγές του demo να μην ακουμπάνε τα real δεδομένα),
# υπάρχουν 2 καθαρές λύσεις:
# 1) Ξεχωριστή DB/schema για demo
# 2) Πεδίο dataset σε όλα τα σχετικά tables (students, appointments, payments, κλπ)

# Όταν αποφασίσεις ποια λύση θες, το ξαναφτιάχνουμε σωστά.
# """

from fastapi import APIRouter

router = APIRouter(prefix="/demo", tags=["demo"])