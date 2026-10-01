import React,{createElement as h} from "react";
import {GEN} from "../data/mock";
import {Btn,Drop,Field} from "../components/ui";

export default function Create(){
 return h("div",null,h("h1",{className:"text-3xl font-extrabold mb-5"},"Yaratish"),h("div",{className:"flex gap-2 mb-6"},h(Btn,{cn:"px-5 py-2 text-sm"},"Reel yaratish"),h(Btn,{v:"g",cn:"px-5 py-2 text-sm"},"Audio kitob yuklash")),h("div",{className:"grid md:grid-cols-2 gap-4 mb-6"},h(Drop,{l:"Video yuklash",accept:"video/*"}),h(Drop,{l:"Kitob muqovasi",accept:"image/*"})),h("div",{className:"glass rounded-3xl p-5"},h(Field,{l:"Kitob nomi",ph:"Masalan: O'tkan kunlar"}),h(Field,{l:"Muallif",ph:"Abdulla Qodiriy"}),h("label",{className:"block mb-4"},h("span",{className:"text-xs text-white/60"},"Janr"),h("select",{className:"mt-1 w-full glass rounded-xl px-4 py-3 outline-none bg-[#0d0d16]"},GEN.map(genre=>h("option",{key:genre},genre)))),h("label",{className:"block mb-4"},h("span",{className:"text-xs text-white/60"},"Tavsif"),h("textarea",{rows:3,className:"mt-1 w-full glass rounded-xl px-4 py-3 outline-none"})),h(Drop,{l:"Audio fayl (mp3)",accept:"audio/*"}),h(Btn,{cn:"w-full py-3 mt-5"},"Joylash")));
}
