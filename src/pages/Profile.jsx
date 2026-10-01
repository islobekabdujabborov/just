import React,{useEffect,useState,createElement as h} from "react";
import {api,itemsFrom,getAccessToken} from "../api";
import {Btn,I} from "../components/ui";

const profileCards=[
 {id:1, title:"O'quv", color:"bg-violet-500/90", icon:"book"},
 {id:2, title:"Kitob", color:"bg-indigo-500/90", icon:"play"},
 {id:3, title:"Saqlangan", color:"bg-emerald-500/90", icon:"save"},
 {id:4, title:"Audio", color:"bg-rose-500/90", icon:"bell"},
 {id:5, title:"Yaxshi", color:"bg-amber-500/90", icon:"star"},
 {id:6, title:"Maqola", color:"bg-sky-500/90", icon:"chat"}
];

export default function Profile({nav}){
 const tabs=["Reels","Audiokitoblar","Yoqtirganlar"];
 const [selected,setSelected]=useState(0);
 const [profile,setProfile]=useState(null);
 const [reels,setReels]=useState([]);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 useEffect(()=>{
  if(!getAccessToken()){
   nav?nav("/login"):window.location.hash="#/login";
   return;
  }
  Promise.all([api.get("/auth/me/"),api.get("/reels/")]).then(([me,payload])=>{
   const list=itemsFrom(payload).filter(reel=>String(reel.author?.id||reel.author_id)===String(me.id));
   setProfile(me);
   setReels(list);
  }).catch(reason=>setError(reason.message)).finally(()=>setLoading(false));
 },[nav]);
 if(loading)return h("div",{className:"text-sm text-slate-500"},"Profil yuklanmoqda...");
 if(!profile)return h("div",{className:"text-sm text-rose-300"},error||"Profil topilmadi");
 const stats=[[String(profile.posts_count||reels.length),"Post"],[String(profile.followers_count||0),"Obunachi"],[String(profile.following_count||0),"Obuna"]];
 return h("div",null,h("div",{className:"flex gap-5 items-center mb-6"},h("div",{className:"h-24 w-24 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-700 grid place-items-center text-2xl font-black glow text-white"},(profile.username||"A").slice(0,1).toUpperCase()),h("div",null,h("h1",{className:"text-2xl font-extrabold text-slate-800"},profile.username),h("p",{className:"text-sm text-slate-500"},profile.bio||"Audiokitob o'quvchi • Toshkent"),h("div",{className:"flex gap-5 my-3 text-sm text-slate-700"},stats.map(([count,label])=>h("div",{key:label},h("b",{className:"font-extrabold text-slate-800"},count)," ",h("span",{className:"text-slate-500"},label)))),h("div",{className:"flex gap-2"},h(Btn,{cn:"px-6 py-2 text-sm"},"Obuna bo'lish"),h(Btn,{v:"g",cn:"px-4 py-2 text-sm"},"Xabar")))),h("div",{className:"flex gap-2 mb-5"},tabs.map((tab,index)=>h("button",{key:tab,onClick:()=>setSelected(index),className:`px-4 py-2 rounded-full text-sm font-semibold ${index===selected?"bg-violet-600 text-white":"glass text-slate-700"}`},tab))),h("div",{className:"grid grid-cols-3 gap-2"},profileCards.map((card)=>h("div",{key:card.id,className:`aspect-[3/4] rounded-xl ${card.color} relative overflow-hidden flex items-center justify-center`},h("div",{className:"absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.28),transparent_25%),linear-gradient(135deg,rgba(255,255,255,0.12),transparent_60%)]"}),h("div",{className:"relative z-10 flex flex-col items-center gap-2 text-white"},h("div",{className:"grid h-12 w-12 place-items-center rounded-full bg-white/15 backdrop-blur-sm"},h(I,{n:card.icon,s:22})),h("span",{className:"text-[10px] font-bold uppercase tracking-[0.25em]"},card.title.slice(0,2)))))));
}
