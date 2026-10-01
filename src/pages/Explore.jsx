import React,{useEffect,useState,createElement as h} from "react";
import {GEN} from "../data/mock";
import {I,Row} from "../components/ui";
import {api,itemsFrom} from "../api";

const genrePalette=[
 {bg:"bg-violet-500/90", icon:"book", color:"text-white"},
 {bg:"bg-indigo-500/90", icon:"search", color:"text-white"},
 {bg:"bg-fuchsia-500/90", icon:"star", color:"text-white"},
 {bg:"bg-emerald-500/90", icon:"play", color:"text-white"},
 {bg:"bg-amber-500/90", icon:"clock", color:"text-white"},
 {bg:"bg-cyan-500/90", icon:"heart", color:"text-white"},
 {bg:"bg-rose-500/90", icon:"chat", color:"text-white"},
 {bg:"bg-sky-500/90", icon:"bell", color:"text-white"}
];

export default function Explore({nav}){
 const [sections,setSections]=useState({trending:[],popular:[],new:[],reels:[],genres:[]});
 const [query,setQuery]=useState("");
 const [results,setResults]=useState(null);
 const [error,setError]=useState("");
 useEffect(()=>{api.get("/explore/").then(setSections).catch(reason=>setError(reason.message));},[]);
 useEffect(()=>{
  if(!query.trim()){setResults(null);return;}
  const timer=setTimeout(()=>api.get(`/search/?q=${encodeURIComponent(query)}`).then(setResults).catch(reason=>setError(reason.message)),250);
  return()=>clearTimeout(timer);
 },[query]);
 const genres=itemsFrom(sections.genres).length?itemsFrom(sections.genres):GEN.map(name=>({name}));
 const searchedBooks=results?itemsFrom(results.books):null;
 return h("div",null,
  h("div",{className:"glass rounded-2xl flex items-center gap-3 px-4 py-3 mb-5"},h(I,{n:"search",s:18}),h("input",{value:query,onChange:event=>setQuery(event.target.value),placeholder:"Kitob, muallif yoki janr qidiring...",className:"bg-transparent outline-none w-full text-sm"})),
  error&&h("p",{role:"alert",className:"text-sm text-rose-300 mb-4"},error),
  h("div",{className:"flex gap-2 overflow-x-auto pb-5"},genres.map((genre,index)=>{
   const palette=genrePalette[index%genrePalette.length];
   return h("button",{key:genre.id||genre.name,className:`shrink-0 flex items-center gap-2 px-3 py-2 rounded-full text-sm font-semibold ${palette.bg} ${palette.color} shadow-sm`,onClick:()=>setQuery(genre.name)},h("span",{className:"grid h-6 w-6 place-items-center rounded-full bg-white/15"},h(I,{n:palette.icon,s:14})),genre.name);
  })),
  searchedBooks?h(Row,{title:"Qidiruv natijalari",items:searchedBooks,nav}):h(React.Fragment,null,
   h(Row,{title:"🔥 Trendda",items:itemsFrom(sections.trending),nav}),
   h(Row,{title:"Mashhur kitoblar",items:itemsFrom(sections.popular),nav}),
   h(Row,{title:"Mashhur Reel'lar",items:itemsFrom(sections.reels),nav}),
   h(Row,{title:"Yangi kitoblar",items:itemsFrom(sections.new),nav})
  )
 );
}
