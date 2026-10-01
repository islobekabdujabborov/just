import React,{useEffect,useState,createElement as h} from "react";
import {GEN,G} from "../data/mock";
import {I,Row} from "../components/ui";
import {api,itemsFrom} from "../api";

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
 return h("div",null,h("div",{className:"glass rounded-2xl flex items-center gap-3 px-4 py-3 mb-5"},h(I,{n:"search",s:18}),h("input",{value:query,onChange:event=>setQuery(event.target.value),placeholder:"Kitob, muallif yoki janr qidiring...",className:"bg-transparent outline-none w-full text-sm"})),
  error&&h("p",{role:"alert",className:"text-sm text-rose-300 mb-4"},error),
  h("div",{className:"flex gap-2 overflow-x-auto pb-5"},genres.map((genre,index)=>h("button",{key:genre.id||genre.name,className:`shrink-0 px-4 py-2 rounded-full text-sm font-semibold bg-gradient-to-br ${G[index%6]} opacity-90 hover:opacity-100`,onClick:()=>setQuery(genre.name)},genre.name))),
  searchedBooks?h(Row,{title:"Qidiruv natijalari",items:searchedBooks,nav}):h(React.Fragment,null,
   h(Row,{title:"🔥 Trendda",items:itemsFrom(sections.trending),nav}),h(Row,{title:"Mashhur kitoblar",items:itemsFrom(sections.popular),nav}),h(Row,{title:"Mashhur Reel'lar",items:itemsFrom(sections.reels),nav}),h(Row,{title:"Yangi kitoblar",items:itemsFrom(sections.new),nav})));
}
