import React,{useEffect,useState,createElement as h} from "react";
import {api} from "../api";
import {I} from "../components/ui";

export default function Notifications(){
 const [items,setItems]=useState([]);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 useEffect(()=>{
  api.get("/notifications/").then(payload=>{setItems(Array.isArray(payload)?payload:payload.results||[]);}).catch(reason=>setError(reason.message)).finally(()=>setLoading(false));
 },[]);
 const markAllRead=async()=>{
  try{await api.post("/notifications/read-all/",{});setItems(previous=>previous.map(item=>({...item,is_read:true})));}
  catch(reason){setError(reason.message);} 
 };
 return h("div",null,
  h("div",{className:"flex items-center justify-between mb-5"},h("h1",{className:"text-3xl font-extrabold"},"Bildirishnomalar"),items.some(item=>!item.is_read)&&h("button",{onClick:markAllRead,className:"text-sm font-semibold text-violet-500"},"Barchasini o'qish")),
  error&&h("p",{role:"alert",className:"text-sm text-rose-300 mb-4"},error),
  loading?h("p",{className:"text-sm text-slate-500"},"Yuklanmoqda..."):items.length===0?h("p",{className:"text-sm text-slate-500"},"Bildirishnoma yo'q."):h("div",{className:"glass rounded-3xl divide-y divide-slate-200"},items.map(item=>h("div",{key:item.id,className:"flex gap-3 p-4 hover:bg-slate-50"},h("span",{className:"h-10 w-10 shrink-0 rounded-full bg-violet-100 text-violet-600 grid place-items-center"},h(I,{n:item.type==="follow"?"user":item.type==="like"?"heart":item.type==="save"?"save":"bell",s:18})),h("div",{className:"flex-1 min-w-0"},h("p",{className:"font-bold text-sm text-slate-800"},item.text),h("p",{className:"text-xs text-slate-500 truncate"},item.time_ago||"hozir")),h("span",{className:`text-[11px] ${item.is_read?"text-slate-400":"text-violet-500 font-bold"}`},item.is_read?"O'qilgan":"Yangi")))));
}
