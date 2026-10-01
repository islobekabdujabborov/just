import React,{useState,createElement as h} from "react";
import {BOOKS,G} from "../data/mock";
import {Btn} from "../components/ui";

export default function Profile(){
 const tabs=["Reels","Audiokitoblar","Yoqtirganlar"];
 const [selected,setSelected]=useState(0);
 return h("div",null,h("div",{className:"flex gap-5 items-center mb-6"},h("div",{className:"h-24 w-24 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-700 grid place-items-center text-2xl font-black glow"},"A"),h("div",null,h("h1",{className:"text-2xl font-extrabold"},"sardor_ovoz"),h("p",{className:"text-sm text-white/60"},"Audiokitob o'quvchi • Toshkent"),h("div",{className:"flex gap-5 my-3 text-sm"},[["48","Post"],["12.4k","Obunachi"],["310","Obuna"]].map(([count,label])=>h("div",{key:label},h("b",null,count)," ",h("span",{className:"text-white/50"},label)))),h("div",{className:"flex gap-2"},h(Btn,{cn:"px-6 py-2 text-sm"},"Obuna bo'lish"),h(Btn,{v:"g",cn:"px-4 py-2 text-sm"},"Xabar")))),h("div",{className:"flex gap-2 mb-5"},tabs.map((tab,index)=>h("button",{key:tab,onClick:()=>setSelected(index),className:`px-4 py-2 rounded-full text-sm font-semibold ${index===selected?"bg-violet-600":"glass"}`},tab))),h("div",{className:"grid grid-cols-3 gap-2"},[...BOOKS,...BOOKS].map((book,index)=>h("div",{key:index,className:`aspect-[3/4] rounded-xl bg-gradient-to-br ${G[index%6]} relative overflow-hidden`},h("div",{className:"absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(255,255,255,0.35),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.15),transparent_60%)]"}),h("span",{className:"relative z-10 text-xs font-black uppercase tracking-[0.3em] text-white/80"},book.t.slice(0,2))))));
}
