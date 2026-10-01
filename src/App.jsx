import React,{useState,useEffect,createElement as h} from "react";
import {BOOKS,G,USERS} from "./data/mock";
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
import {clearTokens} from "./api";

const nav=path=>{location.hash=path};
const useRoute=()=>{const [route,setRoute]=useState(location.hash.slice(1)||"/");useEffect(()=>{const onHashChange=()=>{setRoute(location.hash.slice(1)||"/");window.scrollTo(0,0)};addEventListener("hashchange",onHashChange);return()=>removeEventListener("hashchange",onHashChange)},[]);return route};
const NAV=[["/","Bosh sahifa","home"],["/explore","Kashf etish","search"],["/library","Kutubxona","book"],["/create","Yaratish","plus"],["/notifications","Bildirishnoma","bell"],["/profile","Profil","user"],["/settings","Sozlamalar","gear"]];
const MOB=[["/","home"],["/explore","search"],["/create","plus"],["/library","book"],["/profile","user"]];

export default function App(){
 const route=useRoute();
 const isAuth=route==="/login"||route==="/register";
 const isReelFeed=route==="/";
 const isUserProfile=route.startsWith("/users/");
 const page=route.startsWith("/books/")?h(BookDetail,{id:route.split("/")[2],nav}):isUserProfile?h(Profile,{nav,username:decodeURIComponent(route.slice("/users/".length))}):{
  "/":h(Reels,{nav}),"/explore":h(Explore,{nav}),"/library":h(Library,{nav}),"/profile":h(Profile,{nav}),
  "/create":h(Create,{nav}),"/notifications":h(Notifications,{nav}),"/settings":h(Settings,{nav}),
  "/login":h(Auth,{nav}),"/register":h(Auth,{reg:true,nav})
 }[route]||h(Explore,{nav});
 if(isAuth)return h("div",{className:"min-h-[100dvh] p-6 bg-white"},page);
 return h("div",{className:"flex min-h-[100dvh] bg-white text-black"},
  h("aside",{className:"hidden md:flex flex-col w-60 shrink-0 p-5 border-r border-black/15 bg-white sticky top-0 h-[100dvh] backdrop-blur"},
   h("a",{href:"#/",className:"flex items-center gap-2 mb-8 text-xl font-extrabold"},h("span",{className:"h-8 w-8 rounded-xl bg-black grid place-items-center text-sm font-black text-white"},"A"),h("span",{className:"text-black"},"AvoBook")),
   NAV.map(([path,label,icon])=>h("a",{key:path,href:"#"+path,className:`flex items-center gap-3 px-3 py-2.5 rounded-xl mb-1 text-sm font-semibold ${route===path?"bg-black text-white":"text-black hover:bg-neutral-100"}`},h(I,{n:icon,s:20}),label)),
  h("div",{className:"mt-auto"},h(Btn,{on:()=>{clearTokens();nav("/login")},v:"g",cn:"w-full py-2.5 text-sm"},"Chiqish"))),
  h("main",{className:`flex-1 min-w-0 bg-white ${isReelFeed?"p-0 md:p-4":"p-4 md:p-8 pb-24 md:pb-8"}`},page),
  !isReelFeed&&h("aside",{className:"hidden xl:block w-72 shrink-0 p-5 border-l border-black/15 bg-white backdrop-blur"},
   h("div",{className:"glass rounded-2xl p-4 mb-4"},h("p",{className:"font-bold text-sm mb-3 text-black"},"Davom ettirish"),BOOKS.filter(book=>book.p).map(book=>h("div",{key:book.id,onClick:()=>nav("/books/"+book.id),className:"flex gap-3 mb-3 cursor-pointer"},h("div",{className:`h-11 w-11 rounded-lg bg-gradient-to-br ${G[(book.id-1)%6]} relative overflow-hidden`},h("div",{className:"absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(255,255,255,0.36),transparent_30%)]"})),h("div",{className:"min-w-0"},h("p",{className:"text-xs font-bold truncate text-black"},book.t),h("p",{className:"text-[11px] text-neutral-600"},book.p+"%"))))),
   h("div",{className:"glass rounded-2xl p-4"},h("p",{className:"font-bold text-sm mb-3 text-black"},"Tavsiya etilgan"),USERS.slice(0,3).map(username=>h("div",{key:username,className:"flex items-center gap-2 mb-3"},h("div",{className:"h-8 w-8 rounded-full bg-black/10"}),h("span",{className:"text-xs flex-1 truncate text-black"},"@"+username),h("span",{className:"text-[11px] text-black font-bold"},"Obuna"))))),
  h("nav",{className:"md:hidden fixed bottom-0 inset-x-0 z-40 flex justify-around bg-white/95 backdrop-blur border-t border-black/15 py-3"},MOB.map(([path,icon])=>h("a",{key:path,href:"#"+path,className:icon==="plus"?"h-10 w-12 rounded-xl bg-black grid place-items-center -mt-1 text-white":`grid place-items-center ${route===path?"text-black":"text-neutral-500"}`},h(I,{n:icon,s:22})))))
}
