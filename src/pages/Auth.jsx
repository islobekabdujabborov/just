import React,{useEffect,useMemo,useState,createElement as h} from "react";
import {Btn,Field} from "../components/ui";
import {api,saveTokens} from "../api";

const initialValues={username:"",email:"",identifier:"",password:"",confirmPassword:""};

export default function Auth({reg,nav}){
 const [values,setValues]=useState(initialValues);
 const [error,setError]=useState("");
 const [submitting,setSubmitting]=useState(false);
 const [telegram,setTelegram]=useState({token:"",link:"",status:"idle",code:"",resendSeconds:0,expiresAt:null});
 const update=event=>setValues(previous=>({...previous,[event.target.name]:event.target.value}));

 const codeSummary=useMemo(()=>{
  if(!telegram.expiresAt)return "";
  const remaining=Math.max(0,Math.ceil((new Date(telegram.expiresAt).getTime()-Date.now())/1000));
  return remaining>0?`Kod ${remaining}s ichida amal qiladi.`:"Kod muddati tugadi.";
 },[telegram.expiresAt]);

 const statusPoll=async()=>{
  if(!telegram.token||!reg)return;
  try{
   const result=await api.get(`/auth/telegram/status/?token=${encodeURIComponent(telegram.token)}`);
   if(result.status==="verified"){
    setTelegram(previous=>({...previous,status:"verified"}));
    setError("");
    return;
   }
   if(result.status==="cancelled"||result.status==="expired"){
    setTelegram(previous=>({...previous,status:"idle",token:"",link:"",code:"",expiresAt:null}));
    setError("Tasdiqlash sessiyasi yopildi yoki muddati tugadi.");
   }
  }catch(_error){
   // Ignore transient polling failures for the registration flow.
  }
 };

 useEffect(()=>{
  if(!telegram.token||!reg)return;
  const timer=window.setInterval(statusPoll,3000);
  return ()=>window.clearInterval(timer);
 },[telegram.token,reg]);

 useEffect(()=>{
  if(!telegram.token)return;
  const interval=window.setInterval(()=>{
   setTelegram(previous=>{
    if(!previous.expiresAt) return previous;
    const remaining=Math.max(0,Math.ceil((new Date(previous.expiresAt).getTime()-Date.now())/1000));
    if(remaining<=0){return {...previous,resendSeconds:0};}
    return {...previous,resendSeconds:remaining};
   });
  },1000);
  return ()=>window.clearInterval(interval);
 },[telegram.token]);

 const startTelegramVerification=async()=>{
  setError("");
  if(values.password!==values.confirmPassword){setError("Parollar mos kelmadi.");return;}
  setSubmitting(true);
  try{
   const result=await api.post("/auth/telegram/start/",{username:values.username,email:values.email,password:values.password,confirmPassword:values.confirmPassword});
   setTelegram({token:result.verification_token,link:result.deep_link,status:"pending",code:"",resendSeconds:0,expiresAt:result.expires_at});
   if(result.deep_link){window.open(result.deep_link, "_blank", "noopener,noreferrer");}
  }catch(requestError){setError(requestError.message);}finally{setSubmitting(false);}
 };

 const verifyTelegramCode=async()=>{
  if(!telegram.token||!telegram.code.trim()){
   setError("Tasdiqlash kodini kiriting.");
   return;
  }
  setError("");
  setSubmitting(true);
  try{
   const result=await api.post("/auth/telegram/verify/",{verification_token:telegram.token,code:telegram.code.trim()});
   saveTokens(result);
   const destination="/";
   nav(destination);
  }catch(requestError){setError(requestError.message);}finally{setSubmitting(false);}
 };

 const resendTelegramCode=async()=>{
  if(!telegram.token){return;}
  setError("");
  setSubmitting(true);
  try{
   await api.post("/auth/telegram/resend/",{verification_token:telegram.token});
   setError("Yangi kod yuborildi.");
  }catch(requestError){setError(requestError.message);}finally{setSubmitting(false);}
 };

 const cancelTelegramVerification=async()=>{
  if(!telegram.token)return;
  try{
   await api.post("/auth/telegram/cancel/",{verification_token:telegram.token});
  }catch(_error){
   // ignore cancellation network errors and just clear the UI state
  }
  setTelegram({token:"",link:"",status:"idle",code:"",resendSeconds:0,expiresAt:null});
  setError("");
 };

 const submit=async event=>{
  event.preventDefault();
  setError("");
  if(reg){
   if(!telegram.token){
    await startTelegramVerification();
    return;
   }
   await verifyTelegramCode();
   return;
  }
  if(values.password.length<8){setError("Parol kamida 8 ta belgidan iborat bo'lishi kerak.");return;}
  setSubmitting(true);
  try{
   const result=await api.post("/auth/login/",{username:values.identifier,password:values.password});
   saveTokens(result);
   const destination=sessionStorage.getItem("avobook.returnTo")||"/";
   sessionStorage.removeItem("avobook.returnTo");
   nav(destination);
  }catch(requestError){setError(requestError.message);}finally{setSubmitting(false);}
 };

 return h("div",{className:"max-w-sm mx-auto pt-10"},h("div",{className:"text-center mb-7"},h("div",{className:"mx-auto h-16 w-16 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-700 grid place-items-center text-2xl font-black glow"},"A"),h("h1",{className:"text-3xl font-extrabold mt-2"},"AvoBook"),h("p",{className:"text-sm text-slate-600"},reg?"Yangi hisob yarating":"Hisobingizga kiring")),h("form",{onSubmit:submit,className:"glass rounded-3xl p-6"},reg&&h(Field,{l:"Foydalanuvchi nomi",ph:"sardor_ovoz",name:"username",value:values.username,onChange:update,required:true}),h(Field,{l:reg?"Email":"Email yoki foydalanuvchi nomi",t:reg?"email":"text",ph:reg?"siz@mail.uz":"siz@mail.uz yoki username",name:reg?"email":"identifier",autoComplete:reg?"email":"username",value:reg?values.email:values.identifier,onChange:update,required:true}),h(Field,{l:"Parol",t:"password",ph:"••••••••",name:"password",value:values.password,onChange:update,required:true,minLength:8,autoComplete:reg?"new-password":"current-password"}),reg&&h(Field,{l:"Parolni tasdiqlang",t:"password",ph:"••••••••",name:"confirmPassword",value:values.confirmPassword,onChange:update,required:true,minLength:8,autoComplete:"new-password"}),reg&&telegram.token&&h("div",{className:"mt-4 rounded-2xl border border-violet-200 bg-violet-50 p-3 text-sm text-slate-700"},h("p",{className:"font-semibold mb-2"},"Telegram orqali tasdiqlash"),h("p",{className:"mb-2 text-xs text-slate-600"},"Telegram botga kiring va tasdiqlash kodini oling."),telegram.link&&h("a",{href:telegram.link,target:"_blank",rel:"noopener noreferrer",className:"inline-block mb-3 text-violet-700 font-semibold underline"},"Telegramga o'tish"),h("label",{className:"block text-xs text-slate-600 mb-1"},"6 xonali kod"),h("input",{name:"telegramCode",value:telegram.code,onChange:event=>setTelegram(previous=>({...previous,code:event.target.value.slice(0,6)})),className:"w-full rounded-xl border border-slate-200 px-3 py-2 text-center tracking-[0.5em] font-semibold focus:outline-none focus:ring-2 focus:ring-violet-300",placeholder:"123456",inputMode:"numeric",maxLength:6,autoComplete:"one-time-code"}),h("div",{className:"mt-3 flex gap-2"},h(Btn,{type:"button",cn:"flex-1 py-2 text-sm",onClick:verifyTelegramCode,disabled:submitting},"Tasdiqlash"),h(Btn,{type:"button",cn:"flex-1 py-2 text-sm bg-slate-100 text-slate-700 hover:bg-slate-200",onClick:resendTelegramCode,disabled:submitting},"Qayta yuborish")),h("div",{className:"mt-3 flex items-center justify-between text-xs text-slate-500"},h("span",{className:""},codeSummary||"Kod 5 daqiqa davomida amal qiladi."),h("button",{type:"button",className:"text-slate-700 underline",onClick:cancelTelegramVerification},"Bekor qilish"))),error&&h("p",{role:"alert",className:"text-sm text-rose-600 mb-3 mt-3"},error),!reg&&h(Btn,{type:"submit",cn:"w-full py-3 mt-2",disabled:submitting},submitting?"Kutilmoqda...":"Kirish"),reg&&!telegram.token&&h(Btn,{type:"submit",cn:"w-full py-3 mt-2",disabled:submitting},submitting?"Kutilmoqda...":"Telegram orqali tasdiqlash"),reg&&telegram.token&&h(Btn,{type:"submit",cn:"w-full py-3 mt-2",disabled:submitting},submitting?"Kutilmoqda...":"Tasdiqlashni yakunlash"),h("p",{className:"text-center text-xs text-slate-600 mt-5"},reg?"Hisobingiz bormi? ":"Hisobingiz yo'qmi? ",h("a",{href:reg?"#/login":"#/register",className:"text-black font-bold underline"},reg?"Kirish":"Ro'yxatdan o'tish"))));
}
