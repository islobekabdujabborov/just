import React,{useEffect,useRef,useState} from "react";
import {BOOKS,CH} from "../data/mock";
import {api,itemsFrom} from "../api";
import {Btn,Cover,I,Row} from "../components/ui";

export default function BookDetail({id,nav}){
 const [book,setBook]=useState(BOOKS.find(item=>item.id==id)||BOOKS[0]);
 const [audiobook,setAudiobook]=useState(null);
 const [chapters,setChapters]=useState([]);
 const [relatedBooks,setRelatedBooks]=useState([]);
 const [chapterIndex,setChapterIndex]=useState(0);
 const [error,setError]=useState("");
 const audioRef=useRef(null);
 const savedPosition=useRef(0);
 const lastProgressSent=useRef(-1);
 useEffect(()=>{
  let active=true;
  api.get(`/books/${id}/`).then(result=>{if(active)setBook(result);}).catch(reason=>setError(reason.message));
  api.get("/books/").then(payload=>{if(active)setRelatedBooks(itemsFrom(payload).filter(item=>String(item.id)!==String(id)));}).catch(()=>{});
  api.get("/audiobooks/").then(async payload=>{
   const match=itemsFrom(payload).find(item=>String(item.book?.id)===String(id));
   if(!match||!active)return;
   setAudiobook(match);
   let parts=itemsFrom(match.chapters);
   try{const response=await api.get(`/audiobooks/${match.id}/chapters/`);parts=itemsFrom(response);}catch{}
   if(!active)return;
   setChapters(parts);
   try{const progress=await api.get(`/audiobooks/${match.id}/progress/`);savedPosition.current=progress.position||0;if(progress.chapter){const savedIndex=parts.findIndex(part=>part.id===progress.chapter);if(savedIndex>=0)setChapterIndex(savedIndex);}}catch{}
  }).catch(reason=>{if(active)setError(reason.message);});
  return()=>{active=false;};
 },[id]);
 const activeChapter=chapters[chapterIndex];
 const audioUrl=activeChapter?.audio_url||activeChapter?.audio_file||audiobook?.audio_url||audiobook?.audio_file||"";
 const saveProgress=()=>{
  if(!audiobook||!audioRef.current)return;
  const position=Math.floor(audioRef.current.currentTime||0);
    if(position===lastProgressSent.current)return;
    lastProgressSent.current=position;
  const duration=audioRef.current.duration||activeChapter?.duration||audiobook.duration||0;
  api.post(`/audiobooks/${audiobook.id}/progress/`,{position,percentage:duration?Math.min(100,position/duration*100):0,chapter:activeChapter?.id||null}).catch(()=>{});
 };
 useEffect(()=>{if(audioRef.current&&savedPosition.current){audioRef.current.currentTime=savedPosition.current;savedPosition.current=0;}},[audioUrl]);
 const chapterTitles=chapters.length?chapters:CH.map((title,index)=>({id:index,title,duration:0}));
 return <div>
  <div className="flex flex-col sm:flex-row gap-6 mb-8"><Cover b={book} cn="w-44 h-60 shrink-0"/><div><span className="text-xs px-3 py-1 rounded-full bg-violet-600/25 text-violet-300">{book.g||book.genre?.name||book.genre}</span><h1 className="text-4xl font-extrabold mt-3">{book.t||book.title}</h1><p className="text-white/60">{book.a||book.author?.name}</p><div className="flex gap-4 text-sm text-white/70 my-3"><span className="flex items-center gap-1 text-amber-400"><I n="star" f={1} s={15}/>{book.r||book.rating}</span><span className="flex items-center gap-1"><I n="clock" s={15}/>{book.d||""}</span></div><p className="text-white/70 max-w-xl text-sm">{book.dsc||book.description}</p><div className="flex gap-3 mt-5"><Btn onClick={()=>audioRef.current?.play()} cn="px-6 py-3 flex items-center gap-2"><I n="play" f={1} s={16}/>Hozir tinglash</Btn><Btn v="g" cn="px-4 py-3"><I n="save"/></Btn><Btn v="g" cn="px-4 py-3"><I n="heart"/></Btn></div></div></div>
  {error&&<p role="alert" className="text-sm text-rose-300 mb-4">{error}</p>}
    <div className="glass rounded-3xl p-5 mb-8"><div className="flex items-center gap-4"><div className="h-12 w-12 rounded-full bg-violet-600 grid place-items-center glow"><I n="play" f={1} s={18}/></div><div className="flex-1 min-w-0"><p className="text-sm font-bold">{activeChapter?.title||CH[chapterIndex]||"Audio mavjud emas"}</p><audio key={activeChapter?.id||audiobook?.id} ref={audioRef} controls preload="metadata" src={audioUrl||undefined} onTimeUpdate={event=>{if(Math.floor(event.currentTarget.currentTime)%15===0)saveProgress();}} onPause={saveProgress} onEnded={()=>{saveProgress();if(chapterIndex<chapters.length-1)setChapterIndex(index=>index+1);}} className="mt-2 h-10 w-full"/></div><div className="hidden sm:flex gap-1 items-end h-9">{[...Array(16)].map((_,index)=><span key={index} className="w-1 bg-violet-500/70 rounded" style={{height:`${8+((index*37)%28)}px`}}/>)}</div></div></div>
  <h2 className="font-extrabold mb-3">Boblar</h2><div className="glass rounded-2xl divide-y divide-white/5 mb-8">{chapterTitles.map((chapter,index)=><button key={chapter.id} onClick={()=>setChapterIndex(index)} className={`w-full flex items-center gap-3 px-4 py-3 text-left ${index===chapterIndex?"text-violet-400":""}`}><span className="text-xs w-5 text-white/40">{index+1}</span><span className="flex-1 text-sm">{chapter.title}</span><span className="text-xs text-white/40">{chapter.duration?`${Math.floor(chapter.duration/60)} daq`:""}</span><I n="play" s={14}/></button>)}</div>
    <Row title="Aloqador Reel'lar" items={relatedBooks.slice(0,4)} nav={nav}/><Row title="O'xshash kitoblar" items={[...relatedBooks].reverse().slice(0,4)} nav={nav}/>
 </div>;
}
