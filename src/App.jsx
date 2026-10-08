import React,{useState,useEffect,createElement as h} from "react";
import {Btn,I} from "./components/ui";
import Reels from "./pages/Reels";
import Explore from "./pages/Explore";
import BookDetail from "./pages/BookDetail";
import Library from "./pages/Library";
import Profile from "./pages/Profile";
import Create from "./pages/Create";
import Notifications from "./pages/Notifications";
import Auth from "./pages/Auth";
import Settings from "./pages/Settings";
import {api,clearTokens,getAccessToken} from "./api";

const nav=path=>{location.hash=path};
const useRoute=()=>{const [route,setRoute]=useState(location.hash.slice(1)||"/");useEffect(()=>{const onHashChange=()=>{setRoute(location.hash.slice(1)||"/");window.scrollTo(0,0)};addEventListener("hashchange",onHashChange);return()=>removeEventListener("hashchange",onHashChange)},[]);return route};
const NAV=[["/","Bosh sahifa","home"],["/explore","Kashf etish","search"],["/library","Kutubxona","book"],["/create","Yaratish","plus"],["/notifications","Bildirishnoma","bell"],["/profile","Profil","user"],["/settings","Sozlamalar","gear"]];
const MOB=[["/","home"],["/explore","search"],["/create","plus"],["/library","book"],["/profile","user"]];
const GRADIENTS=["from-violet-600 to-fuchsia-700","from-indigo-600 to-violet-800","from-emerald-600 to-teal-800","from-rose-600 to-purple-800","from-amber-500 to-rose-700","from-sky-600 to-indigo-800"];

export default function App(){
 const route=useRoute();
 const [recommendations,setRecommendations]=useState([]);
 const [installPrompt,setInstallPrompt]=useState(null);
 const [showInstallHelp,setShowInstallHelp]=useState(false);
 const [isInstalled,setIsInstalled]=useState(()=>window.matchMedia("(display-mode: standalone)").matches||window.navigator.standalone===true);
 const isAuth=route==="/login"||route==="/register";
 const isReelFeed=route==="/";
 const isProtectedRoute=["/create","/library","/profile","/notifications","/settings"].includes(route);
 useEffect(()=>{
  if("serviceWorker" in navigator){
   navigator.serviceWorker.register("/service-worker.js").catch(error=>console.error("AvoBook service worker ro'yxatdan o'tmadi:",error));
  }
  const onInstallPrompt=event=>{event.preventDefault();setInstallPrompt(event)};
  const onInstalled=()=>{setIsInstalled(true);setInstallPrompt(null);setShowInstallHelp(false)};
  window.addEventListener("beforeinstallprompt",onInstallPrompt);
  window.addEventListener("appinstalled",onInstalled);
  return ()=>{
   window.removeEventListener("beforeinstallprompt",onInstallPrompt);
   window.removeEventListener("appinstalled",onInstalled);
  };
 },[]);
 useEffect(()=>{
  if(isProtectedRoute&&!getAccessToken()){
   sessionStorage.setItem("avobook.returnTo",route);
   nav("/login");
  }
 },[isProtectedRoute,route]);
 useEffect(()=>{
  let active=true;
  api.get("/explore/").then((data)=>{
   if(!active) return;
   const books = Array.isArray(data?.trending) ? data.trending : Array.isArray(data?.popular) ? data.popular : Array.isArray(data?.new) ? data.new : [];
   setRecommendations(books.slice(0,4));
  }).catch(()=>{
   if(active) setRecommendations([]);
  });
  return ()=>{active=false;};
 },[]);
 const isUserProfile=route.startsWith("/users/");
 const page=isProtectedRoute&&!getAccessToken()?h(Auth,{nav}):route.startsWith("/books/")?h(BookDetail,{id:route.split("/")[2],nav}):isUserProfile?h(Profile,{nav,username:decodeURIComponent(route.slice("/users/".length))}):{
  "/":h(Reels,{nav}),"/explore":h(Explore,{nav}),"/library":h(Library,{nav}),"/profile":h(Profile,{nav}),
  "/create":h(Create,{nav}),"/notifications":h(Notifications,{nav}),"/settings":h(Settings,{nav}),
  "/login":h(Auth,{nav}),"/register":h(Auth,{reg:true,nav})
 }[route]||h(Explore,{nav});
 const installApp=async()=>{
  if(!installPrompt){setShowInstallHelp(true);return}
  await installPrompt.prompt();
  const choice=await installPrompt.userChoice;
  if(choice.outcome==="accepted")setInstallPrompt(null);
 };
 if(isAuth)return h("div",{className:"min-h-[100dvh] p-6 bg-white"},page);
 return h("div",{className:"flex min-h-[100dvh] bg-white text-black"},
  h("aside",{className:"hidden md:flex flex-col w-60 shrink-0 p-5 border-r border-black/15 bg-white sticky top-0 h-[100dvh] backdrop-blur"},
   h("a",{href:"#/",className:"flex items-center gap-2 mb-8 text-xl font-extrabold"},h("span",{className:"h-8 w-8 rounded-xl bg-black grid place-items-center text-sm font-black text-white"},"A"),h("span",{className:"text-black"},"AvoBook")),
   NAV.map(([path,label,icon])=>h("a",{key:path,href:"#"+path,className:`flex items-center gap-3 px-3 py-2.5 rounded-xl mb-1 text-sm font-semibold ${route===path?"bg-black text-white":"text-black hover:bg-neutral-100"}`},h(I,{n:icon,s:20}),label)),
   h("div",{className:"mt-auto"},h(Btn,{on:()=>{clearTokens();nav("/login")},v:"g",cn:"w-full py-2.5 text-sm"},"Chiqish"))
  ),
  h("main",{className:`flex-1 min-w-0 bg-white ${isReelFeed?"p-0 md:p-4":"p-4 md:p-8 pb-24 md:pb-8"}`},page),
  !isReelFeed&&h("aside",{className:"hidden xl:block w-72 shrink-0 p-5 border-l border-black/15 bg-white backdrop-blur"},
   h("div",{className:"glass rounded-2xl p-4 mb-4"},h("p",{className:"font-bold text-sm mb-3 text-black"},"Davom ettirish"),recommendations.length?recommendations.map(book=>h("div",{key:book.id,onClick:()=>nav("/books/"+book.id),className:"flex gap-3 mb-3 cursor-pointer"},h("div",{className:`h-11 w-11 rounded-lg bg-gradient-to-br ${GRADIENTS[(book.id||1)%GRADIENTS.length]} relative overflow-hidden`},h("div",{className:"absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.36),transparent_30%)]"})),h("div",{className:"min-w-0"},h("p",{className:"text-xs font-bold truncate text-black"},book.title||book.t),h("p",{className:"text-[11px] text-neutral-600"},book.author?.name||book.a||"AvoBook")))):h("p",{className:"text-xs text-neutral-600"},"Hozircha tavsiyalar yo'q.")),
   h("div",{className:"glass rounded-2xl p-4"},h("p",{className:"font-bold text-sm mb-3 text-black"},"AvoBook"),h("p",{className:"text-xs text-neutral-600"},"Ko'pchilik xuddi shu sahifada tanlagan audiokitoblarni topadi."))
  ),
  h("nav",{className:"md:hidden fixed bottom-0 inset-x-0 z-40 flex justify-around bg-white/95 backdrop-blur border-t border-black/15 py-3"},MOB.map(([path,icon])=>h("a",{key:path,href:"#"+path,className:icon==="plus"?"h-10 w-12 rounded-xl bg-black grid place-items-center -mt-1 text-white":`grid place-items-center ${route===path?"text-black":"text-neutral-500"}`},h(I,{n:icon,s:22})))),
  !isInstalled&&h("div",{className:"fixed bottom-20 right-4 z-50"},
   h("button",{type:"button",onClick:installApp,className:"rounded-full bg-black px-4 py-3 text-sm font-bold text-white shadow-lg hover:bg-neutral-800"},"Ilovani o'rnatish"),
   showInstallHelp&&h("div",{className:"absolute bottom-14 right-0 w-72 rounded-2xl border border-black/15 bg-white p-4 text-sm text-black shadow-xl",role:"dialog","aria-label":"Ilovani o'rnatish bo'yicha ko'rsatma"},
    h("div",{className:"flex items-start justify-between gap-3"},
     h("p",{className:"font-bold"},"AvoBook'ni qurilmaga o'rnating"),
     h("button",{type:"button",onClick:()=>setShowInstallHelp(false),"aria-label":"Yopish",className:"text-neutral-500"},"×")
    ),
    h("p",{className:"mt-2 text-xs leading-5 text-neutral-600"},"Brauzer menyusini oching va “Ilovani o'rnatish” yoki “Bosh ekranga qo'shish” bandini tanlang.")
   )
  )
 );
}
