import React,{createElement as h} from "react";
import {NOTIF} from "../data/mock";
import {I} from "../components/ui";

export default function Notifications(){
 return h("div",null,h("h1",{className:"text-3xl font-extrabold mb-5"},"Bildirishnomalar"),h("div",{className:"glass rounded-3xl divide-y divide-white/5"},NOTIF.map(([icon,title,summary,time],index)=>h("div",{key:index,className:"flex gap-3 p-4 hover:bg-white/5"},h("span",{className:"h-10 w-10 shrink-0 rounded-full bg-violet-600/20 text-violet-300 grid place-items-center"},h(I,{n:icon,s:18})),h("div",{className:"flex-1 min-w-0"},h("p",{className:"font-bold text-sm"},title),h("p",{className:"text-xs text-white/55 truncate"},summary)),h("span",{className:"text-[11px] text-white/35"},time)))));
}
