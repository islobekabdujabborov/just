import React,{createElement as h} from "react";

export default function Settings(){
 const sections=[["Hisob",["Profilni tahrirlash","Parolni o'zgartirish","Bog'langan hisoblar"]],["Ko'rinish",["Qorong'i rejim","Shrift o'lchami"]],["Bildirishnomalar",["Like va izohlar","Yangi obunachilar","Yangi kitoblar"]],["Maxfiylik",["Yopiq hisob","Bloklanganlar"]],["Til",["O'zbekcha","Ruscha","English"]]];
 return h("div",null,h("h1",{className:"text-3xl font-extrabold mb-5"},"Sozlamalar"),sections.map(([section,items])=>h("div",{key:section,className:"mb-6"},h("h2",{className:"text-xs uppercase tracking-wider text-white/40 mb-2"},section),h("div",{className:"glass rounded-2xl divide-y divide-white/5"},items.map(item=>h("div",{key:item,className:"flex justify-between items-center px-4 py-3 text-sm hover:bg-white/5"},item,h("span",{className:"h-5 w-9 rounded-full bg-violet-600/40 relative"},h("span",{className:"absolute right-0.5 top-0.5 h-4 w-4 rounded-full bg-violet-400"}))))))));
}
