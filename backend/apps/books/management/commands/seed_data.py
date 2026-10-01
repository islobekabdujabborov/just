from django.core.management.base import BaseCommand
from apps.users.models import Follow, User
from apps.books.models import Author, Book, Genre
from apps.audiobooks.models import Audiobook, Chapter
from apps.reels.models import Reel
from apps.interactions.models import Like, Save
from apps.comments.models import Comment
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = "Create Uzbek AvoBook demonstration data."

    def handle(self, *args, **options):
        genre_names = ["Roman", "Detektiv", "Fantastika", "Biznes", "Psixologiya", "Tarix", "Ta'lim", "Sarguzasht", "She'r", "Hikoya"]
        genres = {name: Genre.objects.get_or_create(name=name, defaults={"slug": name.lower().replace("'", "").replace(" ", "-")})[0] for name in genre_names}
        users = []
        for username, email in [("sardor_ovoz", "sardor@example.uz"), ("dilnoza_reads", "dilnoza@example.uz"), ("kitobxon_uz", "kitobxon@example.uz"), ("audio_jasur", "jasur@example.uz"), ("malika_books", "malika@example.uz")]:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email, "bio": "AvoBook kitobxonlar hamjamiyati"})
            if created: user.set_password("AvoBook123!"); user.save()
            users.append(user)
        titles = [
            ("O'tkan kunlar", "Abdulla Qodiriy", "Roman", 45600, 4.9, "Otabek va Kumushning fojiali sevgisi — o'zbek romanchiligining ilk va eng buyuk namunasi."),
            ("Ikki eshik orasi", "O'tkir Hoshimov", "Roman", 50700, 4.8, "Urush va undan keyingi avlod taqdiri haqida ko'p ovozli, hayajonli hikoya."),
            ("Mehrobdan chayon", "Abdulla Qodiriy", "Tarix", 40800, 4.7, "Xon saroyidagi fitna va Anvarning taqdiri haqida tarixiy roman."),
            ("Dunyo ishlari", "O'tkir Hoshimov", "Hikoya", 21000, 4.9, "Ona mehri va oddiy insonlar hayoti haqidagi ta'sirchan hikoyalar to'plami."),
            ("Alkimyogar", "Paulo Coelho", "Sarguzasht", 22500, 4.6, "Santyagoning xazina izlab ketgan yo'li — o'z afsonangni topish haqida."),
            ("Boylik psixologiyasi", "Morgan Housel", "Biznes", 27000, 4.5, "Pul haqida qaror qabul qilish — aql emas, xulq-atvor masalasi ekani haqida."),
        ]
        books = []
        for title, author_name, genre_name, duration, rating, description in titles:
            author, _ = Author.objects.get_or_create(name=author_name)
            book, _ = Book.objects.get_or_create(title=title, defaults={"author": author, "genre": genres[genre_name], "duration": duration, "rating": rating, "description": description, "language": "uz"})
            books.append(book)
            audiobook, _ = Audiobook.objects.get_or_create(book=book, defaults={"duration": duration, "created_by": users[0]})
            for order, title_part in enumerate(["Muqaddima", "Birinchi bob", "Ikkinchi bob", "Uchinchi bob", "Xotima"], start=1):
                Chapter.objects.get_or_create(audiobook=audiobook, order=order, defaults={"title": title_part, "duration": duration // 5})
        reels = []
        for index, book in enumerate(books):
            reel, _ = Reel.objects.get_or_create(author=users[index % len(users)], book=book, defaults={"caption": f"{book.title} asarini tinglash taassurotlari"})
            reels.append(reel)
        for index, reel in enumerate(reels):
            Like.objects.get_or_create(user=users[(index + 1) % len(users)], reel=reel)
            Save.objects.get_or_create(user=users[(index + 2) % len(users)], reel=reel)
            Comment.objects.get_or_create(user=users[(index + 3) % len(users)], reel=reel, defaults={"text": "Ajoyib asar, tinglashni tavsiya qilaman!"})
            Follow.objects.get_or_create(follower=users[(index + 1) % len(users)], followed=users[index % len(users)])
        for user in users:
            Notification.objects.get_or_create(recipient=user, actor=users[1], type="new_audiobook", text="Yangi o'zbek audiokitoblari qo'shildi")
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(users)} users, {len(books)} books, {len(reels)} reels, chapters, interactions, and notifications."))