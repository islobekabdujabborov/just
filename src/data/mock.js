export const G=["from-violet-600 to-fuchsia-700","from-indigo-600 to-violet-800","from-emerald-600 to-teal-800","from-rose-600 to-purple-800","from-amber-500 to-rose-700","from-sky-600 to-indigo-800"];
export const BOOKS=[
 {id:1,t:"O'tkan kunlar",a:"Abdulla Qodiriy",g:"Roman",r:4.9,d:"12s 40d",p:72,dsc:"Otabek va Kumushning fojiali sevgisi — o'zbek romanchiligining ilk va eng buyuk namunasi."},
 {id:2,t:"Ikki eshik orasi",a:"O'tkir Hoshimov",g:"Roman",r:4.8,d:"14s 05d",p:38,dsc:"Urush va undan keyingi avlod taqdiri haqida ko'p ovozli, hayajonli hikoya."},
 {id:3,t:"Mehrobdan chayon",a:"Abdulla Qodiriy",g:"Tarix",r:4.7,d:"11s 20d",p:0,dsc:"Xon saroyidagi fitna va Anvarning taqdiri haqida tarixiy roman."},
 {id:4,t:"Alkimyogar",a:"Paulo Coelho",g:"Sarguzasht",r:4.6,d:"6s 15d",p:91,dsc:"Santyagoning xazina izlab ketgan yo'li — o'z afsonangni topish haqida."},
 {id:5,t:"Dunyo ishlari",a:"O'tkir Hoshimov",g:"Hikoya",r:4.9,d:"5s 50d",p:12,dsc:"Ona mehri va oddiy insonlar hayoti haqidagi ta'sirchan hikoyalar to'plami."},
 {id:6,t:"Boylik psixologiyasi",a:"Morgan Housel",g:"Biznes",r:4.5,d:"7s 30d",p:0,dsc:"Pul haqida qaror qabul qilish — aql emas, xulq-atvor masalasi ekani haqida."}
];
export const GEN=["Roman","Detektiv","Fantastika","Biznes","Psixologiya","Tarix","Ta'lim","Sarguzasht","She'r"];
export const USERS=["dilnoza_reads","kitobxon_uz","audio_jasur","malika.books","sardor_ovoz"];
export const REELS=BOOKS.map((book,index)=>({...book,u:USERS[index%5],likes:(12+index*7)+"k",cm:120+index*33,cap:"Bu asarni tunda tinglang — butunlay boshqa his"}));
export const NOTIF=[["heart","Reelingizga like bosildi",'dilnoza_reads sizning "Alkimyogar" reelingizni yoqtirdi',"2 daqiqa"],["user","Yangi follower","kitobxon_uz sizga obuna bo'ldi","18 daqiqa"],["chat","Comment yozildi",'audio_jasur: "Ovozingiz juda yoqdi!"',"1 soat"],["save","Kitobingiz saqlandi",'malika.books "Dunyo ishlari"ni saqladi',"3 soat"],["book","Yangi audiobook chiqdi",'"Mehrobdan chayon" endi platformada',"Kecha"]];
export const CH=["Muqaddima","Birinchi bob — Marg'ilon","Ikkinchi bob — Toshkent yo'li","Uchinchi bob — Qutidor uyi","To'rtinchi bob — Xiyonat","Xotima"];
