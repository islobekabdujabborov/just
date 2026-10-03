import React,{useState,createElement as h} from "react";
import {Btn,Field} from "../components/ui";
import {api,saveTokens} from "../api";

export default function Auth({reg,nav}){
 const [values,setValues]=useState({username:"",email:"",identifier:"",password:"",confirmPassword:""});
 const [error,setError]=useState("");
 const [submitting,setSubmitting]=useState(false);
 const update=event=>setValues(previous=>({...previous,[event.target.name]:event.target.value}));
 const submit=async event=>{
  event.preventDefault();setError("");
  if(reg&&values.password!==values.confirmPassword){setError("Parollar mos kelmadi.");return;}
  setSubmitting(true);
  try{
    const result=reg?await api.post("/auth/register/",{username:values.username,email:values.email,password:values.password}):await api.post("/auth/login/",{username:values.identifier,password:values.password});
    saveTokens(result);
    const destination=reg?"/":sessionStorage.getItem("avobook.returnTo")||"/";
    sessionStorage.removeItem("avobook.returnTo");
    nav(destination);
  }catch(requestError){setError(requestError.message);}finally{setSubmitting(false);}
 };
 return h("div",{className:"max-w-sm mx-auto pt-10"},h("div",{className:"text-center mb-7"},h("div",{className:"mx-auto h-16 w-16 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-700 grid place-items-center text-2xl font-black glow"},"A"),h("h1",{className:"text-3xl font-extrabold mt-2"},"AvoBook"),h("p",{className:"text-sm text-slate-600"},reg?"Yangi hisob yarating":"Hisobingizga kiring")),h("form",{onSubmit:submit,className:"glass rounded-3xl p-6"},reg&&h(Field,{l:"Foydalanuvchi nomi",ph:"sardor_ovoz",name:"username",value:values.username,onChange:update,required:true}),h(Field,{l:reg?"Email":"Email yoki foydalanuvchi nomi",t:reg?"email":"text",ph:reg?"siz@mail.uz":"siz@mail.uz yoki username",name:reg?"email":"identifier",autoComplete:reg?"email":"username",value:reg?values.email:values.identifier,onChange:update,required:true}),h(Field,{l:"Parol",t:"password",ph:"••••••••",name:"password",value:values.password,onChange:update,required:true,minLength:8,autoComplete:reg?"new-password":"current-password"}),reg&&h(Field,{l:"Parolni tasdiqlang",t:"password",ph:"••••••••",name:"confirmPassword",value:values.confirmPassword,onChange:update,required:true,minLength:8,autoComplete:"new-password"}),error&&h("p",{role:"alert",className:"text-sm text-rose-600 mb-3"},error),h(Btn,{type:"submit",cn:"w-full py-3 mt-2",disabled:submitting},submitting?"Kutilmoqda...":reg?"Ro'yxatdan o'tish":"Kirish"),h("p",{className:"text-center text-xs text-slate-600 mt-5"},reg?"Hisobingiz bormi? ":"Hisobingiz yo'qmi? ",h("a",{href:reg?"#/login":"#/register",className:"text-black font-bold underline"},reg?"Kirish":"Ro'yxatdan o'tish"))));
}
