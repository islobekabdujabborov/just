import React,{useEffect,useRef,useState} from "react";
import {GEN} from "../data/mock";
import {I,Row} from "../components/ui";
import {api,itemsFrom} from "../api";

const genrePalette=[
 {bg:"bg-violet-500/90",icon:"book"},{bg:"bg-indigo-500/90",icon:"search"},
 {bg:"bg-fuchsia-500/90",icon:"star"},{bg:"bg-emerald-500/90",icon:"play"},
 {bg:"bg-amber-500/90",icon:"clock"},{bg:"bg-cyan-500/90",icon:"heart"},
 {bg:"bg-rose-500/90",icon:"chat"},{bg:"bg-sky-500/90",icon:"bell"}
];

export default function Explore({nav}){
 const [sections,setSections]=useState({trending:[],popular:[],new:[],reels:[],genres:[]});
 const [query,setQuery]=useState("");
 const [results,setResults]=useState(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const [searching,setSearching]=useState(false);
 const requestId=useRef(0);

 useEffect(()=>{
  let active=true;
  api.get("/explore/").then(data=>{if(active)setSections(data);}).catch(reason=>{if(active)setError(reason.message);}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;};
 },[]);

 useEffect(()=>{
  const value=query.trim();
  const current=++requestId.current;
  if(!value){setResults(null);setSearching(false);setError("");return;}
  const timer=setTimeout(()=>{
   setSearching(true);
   setError("");
   api.get(`/search/?q=${encodeURIComponent(value)}`).then(data=>{
    if(requestId.current===current)setResults(data);
   }).catch(reason=>{
    if(requestId.current===current)setError(reason.message);
   }).finally(()=>{
    if(requestId.current===current)setSearching(false);
   });
  },250);
  return()=>clearTimeout(timer);
 },[query]);

 const genres=itemsFrom(sections.genres).length?itemsFrom(sections.genres):GEN.map(name=>({name}));
 const books=itemsFrom(results?.books);
 const users=itemsFrom(results?.users);
 const reels=itemsFrom(results?.reels);
 const hasResults=books.length+users.length+reels.length>0;

 return <div>
  <form onSubmit={event=>event.preventDefault()} className="glass rounded-2xl flex items-center gap-3 px-4 py-3 mb-5">
   <I n="search" s={18}/>
   <input aria-label="Kitob, muallif yoki janr qidirish" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Kitob, muallif yoki janr qidiring..." className="bg-transparent outline-none w-full min-w-0 text-sm"/>
   <button type="submit" aria-label="Qidirish" title="Qidirish" className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-black text-white"><I n="search" s={16}/></button>
  </form>
  {error&&<p role="alert" className="text-sm text-rose-700 mb-4">{error}</p>}

  {results===null&&<>
   <div className="flex gap-2 overflow-x-auto pb-5" aria-label="Janrlar">
    {genres.map((genre,index)=>{
     const palette=genrePalette[index%genrePalette.length];
     return <button type="button" key={genre.id||genre.name} className={`shrink-0 flex items-center gap-2 px-3 py-2 rounded-full text-sm font-semibold ${palette.bg} text-white shadow-sm`} onClick={()=>setQuery(genre.name)}><span className="grid h-6 w-6 place-items-center rounded-full bg-white/15"><I n={palette.icon} s={14}/></span>{genre.name}</button>;
    })}
   </div>
   {loading?<p role="status" className="text-sm text-slate-600">Kitoblar yuklanmoqda...</p>:<>
    {sections.trending?.length>0&&<Row title="Trendda" items={itemsFrom(sections.trending)} nav={nav}/>}
    {sections.popular?.length>0&&<Row title="Mashhur kitoblar" items={itemsFrom(sections.popular)} nav={nav}/>}
    {sections.reels?.length>0&&<Row title="Mashhur Reel'lar" items={itemsFrom(sections.reels)} nav={nav}/>}
    {sections.new?.length>0&&<Row title="Yangi kitoblar" items={itemsFrom(sections.new)} nav={nav}/>}
    {!sections.trending?.length&&!sections.popular?.length&&!sections.reels?.length&&!sections.new?.length&&<div className="py-10 text-center"><h2 className="font-bold">Hozircha kitoblar yo'q</h2><p className="text-sm text-slate-600 mt-1">Yangi kitob va reelslar shu yerda ko'rinadi.</p></div>}
   </>}
  </>}

  {results!==null&&(searching?<p role="status" className="text-sm text-slate-600">Qidirilmoqda...</p>:!hasResults?<p className="py-10 text-center text-sm text-slate-600">"{query.trim()}" bo'yicha natija topilmadi.</p>:<>
   {books.length>0&&<Row title="Kitoblar" items={books} nav={nav}/>}
   {users.length>0&&<section className="mb-8"><h2 className="font-extrabold mb-3">Foydalanuvchilar</h2><div className="grid gap-2 sm:grid-cols-2">{users.map(user=><button type="button" key={user.id} onClick={()=>nav(`/users/${encodeURIComponent(user.username)}`)} className="glass flex min-w-0 items-center gap-3 rounded-xl p-3 text-left hover:bg-neutral-100">{user.avatar?<img src={user.avatar} alt="" loading="lazy" className="h-10 w-10 rounded-full object-cover"/>:<span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-black text-white">{user.username?.slice(0,1).toUpperCase()}</span>}<span className="truncate font-semibold">@{user.username}</span></button>)}</div></section>}
   {reels.length>0&&<section className="mb-8"><h2 className="font-extrabold mb-3">Reellar</h2><div className="grid gap-2 sm:grid-cols-2">{reels.map(reel=><button type="button" key={reel.id} onClick={()=>reel.author?.username&&nav(`/users/${encodeURIComponent(reel.author.username)}`)} className="glass min-w-0 rounded-xl p-3 text-left hover:bg-neutral-100"><span className="block truncate font-semibold">{reel.caption||reel.cap||reel.t||"Reel"}</span><span className="block truncate text-sm text-slate-600">@{reel.author?.username||reel.u||"kitobxon"}</span></button>)}</div></section>}
  </>)}
 </div>;
}