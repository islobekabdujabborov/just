import React,{useEffect,useMemo,useState} from "react";
import {Btn,Field} from "../components/ui";
import {api,saveTokens} from "../api";
import {QRCodeSVG} from "qrcode.react";

const initialValues={username:"",email:"",identifier:"",password:"",confirmPassword:""};

export default function Auth({reg,nav}){
 const [values,setValues]=useState(initialValues);
 const [error,setError]=useState("");
 const [submitting,setSubmitting]=useState(false);
 const [telegram,setTelegram]=useState({token:"",link:"",status:"idle",code:"",resendSeconds:0,expiresAt:null});
 const [linkStartedAt,setLinkStartedAt]=useState(null);
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
   if(result.status==="linked"){
    setTelegram(previous=>({...previous,status:"linked"}));
    setError("");
    return;
   }
   if(result.status==="pending"){
    setTelegram(previous=>({...previous,status:"pending"}));
   }
   if(result.status==="cancelled"||result.status==="expired"){
    setTelegram(previous=>({...previous,status:"idle",token:"",link:"",code:"",expiresAt:null}));
    setLinkStartedAt(null);
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
   setLinkStartedAt(Date.now());
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
  setLinkStartedAt(null);
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

 return <div className="mx-auto max-w-sm pt-10">
  <div className="mb-7 text-center">
   <div className="glow mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-700 text-2xl font-black">A</div>
   <h1 className="mt-2 text-3xl font-extrabold">AvoBook</h1>
   <p className="text-sm text-slate-600">{reg?"Yangi hisob yarating":"Hisobingizga kiring"}</p>
  </div>
  <form onSubmit={submit} className="glass rounded-3xl p-6">
   {reg&&<Field l="Foydalanuvchi nomi" ph="sardor_ovoz" name="username" value={values.username} onChange={update} required/>}
   <Field l={reg?"Email":"Email yoki foydalanuvchi nomi"} t={reg?"email":"text"} ph={reg?"siz@mail.uz":"siz@mail.uz yoki username"} name={reg?"email":"identifier"} autoComplete={reg?"email":"username"} value={reg?values.email:values.identifier} onChange={update} required/>
   <Field l="Parol" t="password" ph="••••••••" name="password" value={values.password} onChange={update} required minLength={8} autoComplete={reg?"new-password":"current-password"}/>
   {reg&&<Field l="Parolni tasdiqlang" t="password" ph="••••••••" name="confirmPassword" value={values.confirmPassword} onChange={update} required minLength={8} autoComplete="new-password"/>}
   {reg&&telegram.token&&<div className="mt-4 rounded-2xl border border-violet-200 bg-violet-50 p-4 text-sm text-slate-700">
    <p className="mb-3 font-semibold">Telegram orqali tasdiqlash</p>
    {telegram.link&&<a href={telegram.link} target="_blank" rel="noopener noreferrer" className="mb-4 flex w-full items-center justify-center rounded-2xl bg-black px-5 py-3 text-center font-bold text-white transition hover:bg-neutral-800">Telegramni ochish</a>}
    <p role="status" aria-live="polite" className="mb-3 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-violet-900">
     {telegram.status==="linked"||telegram.status==="verified"?"Telegram bog'landi, kodni kiriting":"Telegram kutilmoqda..."}
    </p>
    <div className="mb-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
     <ol className="list-decimal space-y-2 pl-5 text-sm leading-5">
      <li>«Telegramni ochish» tugmasini bosing.</li>
      <li>Telegramda START tugmasini bosing (/start ni qo'lda yozmang).</li>
      <li>Bot yuborgan 6 xonali kodni shu yerga kiriting.</li>
     </ol>
     {telegram.link&&<div className="hidden rounded-xl bg-white p-3 text-center md:block">
      <QRCodeSVG value={telegram.link} size={144} level="M" includeMargin/>
      <p className="mt-2 text-xs text-slate-600">Telefoningiz bilan skanerlang</p>
     </div>}
    </div>
    {linkStartedAt&&telegram.status!=="linked"&&telegram.status!=="verified"&&Date.now()-linkStartedAt>=30000&&<p className="mb-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs font-medium text-amber-900">Telegramda START tugmasini bosdingizmi? Havola orqali kirish shart.</p>}
    <label htmlFor="telegram-code" className="mb-1 block text-xs text-slate-600">6 xonali kod</label>
    <input id="telegram-code" name="telegramCode" value={telegram.code} onChange={event=>setTelegram(previous=>({...previous,code:event.target.value.replace(/\D/g,"").slice(0,6)}))} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-center font-semibold tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-violet-300" placeholder="123456" inputMode="numeric" maxLength={6} autoComplete="one-time-code"/>
    <div className="mt-3 flex gap-2">
     <Btn type="button" cn="flex-1 py-2 text-sm" onClick={verifyTelegramCode} disabled={submitting}>Tasdiqlash</Btn>
     <Btn type="button" v="g" cn="flex-1 py-2 text-sm" onClick={resendTelegramCode} disabled={submitting}>Qayta yuborish</Btn>
    </div>
    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-500">
     <span>{codeSummary||"Kod 5 daqiqa davomida amal qiladi."}</span>
     <button type="button" className="shrink-0 text-slate-700 underline" onClick={cancelTelegramVerification}>Bekor qilish</button>
    </div>
   </div>}
   {error&&<p role="alert" className="mb-3 mt-3 text-sm text-rose-600">{error}</p>}
   {!reg&&<Btn type="submit" cn="mt-2 w-full py-3" disabled={submitting}>{submitting?"Kutilmoqda...":"Kirish"}</Btn>}
   {reg&&!telegram.token&&<Btn type="submit" cn="mt-2 w-full py-3" disabled={submitting}>{submitting?"Kutilmoqda...":"Telegram orqali tasdiqlash"}</Btn>}
   {reg&&telegram.token&&<Btn type="submit" cn="mt-2 w-full py-3" disabled={submitting}>{submitting?"Kutilmoqda...":"Tasdiqlashni yakunlash"}</Btn>}
   <p className="mt-5 text-center text-xs text-slate-600">{reg?"Hisobingiz bormi? ":"Hisobingiz yo'qmi? "}<a href={reg?"#/login":"#/register"} className="font-bold text-black underline">{reg?"Kirish":"Ro'yxatdan o'tish"}</a></p>
  </form>
 </div>;
}
