import React,{useEffect,useRef,useState} from "react";
import {api,getAccessToken,itemsFrom} from "../api";
import {Btn,Cover,I,Row} from "../components/ui";

export default function BookDetail({id,nav}){
 const [book,setBook]=useState(null);
 const [audiobook,setAudiobook]=useState(null);
 const [chapters,setChapters]=useState([]);
 const [relatedBooks,setRelatedBooks]=useState([]);
 const [chapterIndex,setChapterIndex]=useState(0);
 const [isLiked,setIsLiked]=useState(false);
 const [isSaved,setIsSaved]=useState(false);
 const [loading,setLoading]=useState(true);
 const [audioError,setAudioError]=useState("");
 const [error,setError]=useState("");
 const audioRef=useRef(null);
 const savedPosition=useRef(0);
 const lastProgressSent=useRef(0);

 useEffect(()=>{
  let active=true;
  setLoading(true);
  setError("");
  setAudioError("");
  setBook(null);
  setAudiobook(null);
  setChapters([]);
  setChapterIndex(0);
  savedPosition.current=0;
  lastProgressSent.current=0;
  Promise.all([api.get(`/books/${id}/`),api.get("/books/").catch(()=>[]),api.get("/audiobooks/").catch(()=>[])]).then(async([bookResult,booksPayload,audioPayload])=>{
   if(!active)return;
   setBook(bookResult);
   setIsLiked(Boolean(bookResult.is_liked));
   setIsSaved(Boolean(bookResult.is_saved));
   setRelatedBooks(itemsFrom(booksPayload).filter(item=>String(item.id)!==String(id)));
   const match=itemsFrom(audioPayload).find(item=>String(item.book?.id)===String(id));
   if(!match)return;
   setAudiobook(match);
   let parts=itemsFrom(match.chapters);
   try{parts=itemsFrom(await api.get(`/audiobooks/${match.id}/chapters/`));}catch{}
   if(!active)return;
   setChapters(parts);
   if(getAccessToken()){
    try{
     const progress=await api.get(`/audiobooks/${match.id}/progress/`);
     if(!active)return;
     savedPosition.current=progress.position||0;
     if(progress.chapter){const savedIndex=parts.findIndex(part=>part.id===progress.chapter);if(savedIndex>=0)setChapterIndex(savedIndex);}
    }catch{}
   }
  }).catch(reason=>{if(active)setError(reason.message);}).finally(()=>{if(active)setLoading(false);});
  return()=>{
   active=false;
   audioRef.current?.pause();
  };
 },[id]);

 const activeChapter=chapters[chapterIndex];
 const audioUrl=activeChapter?.audio_url||activeChapter?.audio_file||audiobook?.audio_url||audiobook?.audio_file||"";
 const saveProgress=(force=false)=>{
  const player=audioRef.current;
  if(!getAccessToken()||!audiobook||!player)return;
  const position=Math.floor(player.currentTime||0);
  if(!force&&position-lastProgressSent.current<15)return;
  lastProgressSent.current=position;
  const duration=player.duration||activeChapter?.duration||audiobook.duration||0;
  api.post(`/audiobooks/${audiobook.id}/progress/`,{position,percentage:duration?Math.min(100,position/duration*100):0,chapter:activeChapter?.id||null}).catch(()=>{});
 };
 const toggleBookInteraction=async action=>{
  const active=action==="like"?isLiked:isSaved;
  try{
   const result=active?await api.delete(`/books/${id}/${action}/`):await api.post(`/books/${id}/${action}/`);
   if(action==="like")setIsLiked(result.is_liked);
   else setIsSaved(result.is_saved);
  }catch(reason){setError(reason.message);}
 };
 const playAudio=()=>{
  if(!audioUrl){setAudioError("Bu kitob uchun audio hali yuklanmagan.");return;}
  audioRef.current?.play().then(()=>setAudioError("")).catch(()=>setAudioError("Ijro boshlanmadi. Audio pleerdagi Play tugmasini bosing."));
 };
 useEffect(()=>{
  const player=audioRef.current;
  if(player&&savedPosition.current){player.currentTime=savedPosition.current;savedPosition.current=0;}
 },[audioUrl]);
 const setChapter=index=>{
  setChapterIndex(index);
  savedPosition.current=0;
  setAudioError("");
 };

 if(loading)return <p role="status" className="py-8 text-sm text-slate-600">Kitob yuklanmoqda...</p>;
 if(!book)return <div><p role="alert" className="text-sm text-rose-700">{error||"Kitob topilmadi."}</p><button type="button" onClick={()=>nav("/explore")} className="mt-3 text-sm font-bold underline">Kitoblarni ko'rish</button></div>;
 const title=book.title||book.t||"Nomsiz kitob";
 const author=book.author?.name||book.a||"Muallif noma'lum";
 const genre=book.genre?.name||book.g||book.genre||"Janr ko'rsatilmagan";
 const description=book.description||book.dsc||"Tavsif kiritilmagan.";

 return <div>
  <div className="flex flex-col sm:flex-row gap-6 mb-8">
   <div className="w-44 h-60 shrink-0">{book.cover?<img src={book.cover} alt={`${title} muqovasi`} loading="lazy" className="h-full w-full rounded-2xl object-cover"/>:<Cover b={book} cn="h-full w-full"/>}</div>
   <div className="min-w-0">
    <span className="inline-block text-xs px-3 py-1 rounded-full bg-black text-white">{genre}</span>
    <h1 className="text-3xl sm:text-4xl font-extrabold mt-3 break-words">{title}</h1>
    <p className="text-slate-600">{author}</p>
    <div className="flex flex-wrap gap-4 text-sm text-slate-600 my-3"><span className="flex items-center gap-1"><I n="star" f={1} s={15}/>{book.r||book.rating||"Baholanmagan"}</span><span className="flex items-center gap-1"><I n="clock" s={15}/>{book.d||"Davomiyligi noma'lum"}</span></div>
    <p className="max-w-xl text-sm text-slate-700 whitespace-pre-wrap">{description}</p>
    <div className="flex flex-wrap gap-3 mt-5">
     <Btn onClick={playAudio} cn="px-6 py-3 flex items-center gap-2"><I n="play" f={1} s={16}/>Tinglash</Btn>
     <Btn v="g" onClick={()=>toggleBookInteraction("save")} aria-label={isSaved?"Saqlanganlardan olib tashlash":"Saqlash"} aria-pressed={isSaved} cn="px-4 py-3"><I n="save" f={isSaved?1:0}/></Btn>
     <Btn v="g" onClick={()=>toggleBookInteraction("like")} aria-label={isLiked?"Yoqtirishdan olib tashlash":"Yoqtirish"} aria-pressed={isLiked} cn="px-4 py-3"><I n="heart" f={isLiked?1:0}/></Btn>
    </div>
   </div>
  </div>
  {error&&<p role="alert" className="text-sm text-rose-700 mb-4">{error}</p>}
  <section className="glass rounded-2xl p-4 sm:p-5 mb-8" aria-label="Audio player">
   <div className="flex flex-col sm:flex-row sm:items-center gap-3">
    <div className="flex-1 min-w-0"><p className="text-sm font-bold truncate">{activeChapter?.title||title}</p>
     <audio key={activeChapter?.id||audiobook?.id||id} ref={audioRef} controls preload="metadata" src={audioUrl||undefined} onTimeUpdate={()=>saveProgress()} onPause={()=>saveProgress(true)} onEnded={()=>{saveProgress(true);if(chapterIndex<chapters.length-1)setChapter(chapterIndex+1);}} onError={()=>setAudioError("Audio faylni yuklab bo'lmadi.")} className="mt-2 h-10 w-full"/>
    </div>
    <div className="flex gap-2 justify-end">
     <Btn v="g" disabled={!chapters.length||chapterIndex===0} aria-label="Oldingi bob" onClick={()=>setChapter(chapterIndex-1)} cn="px-3 py-2"><I n="up" s={18}/></Btn>
     <Btn v="g" disabled={!chapters.length||chapterIndex>=chapters.length-1} aria-label="Keyingi bob" onClick={()=>setChapter(chapterIndex+1)} cn="px-3 py-2"><I n="up" s={18}/></Btn>
    </div>
   </div>
   {!audioUrl&&!audioError&&<p className="text-sm text-slate-600 mt-2">Audio hali mavjud emas.</p>}
   {audioError&&<p role="alert" className="text-sm text-rose-700 mt-2">{audioError}</p>}
  </section>
  <h2 className="font-extrabold mb-3">Boblar</h2>
  {chapters.length?<div className="glass rounded-2xl divide-y divide-black/10 mb-8">{chapters.map((chapter,index)=><button key={chapter.id} type="button" onClick={()=>setChapter(index)} aria-current={index===chapterIndex?"true":undefined} className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-neutral-100 ${index===chapterIndex?"font-bold":""}`}><span className="text-xs w-5 text-slate-500">{index+1}</span><span className="flex-1 min-w-0 text-sm truncate">{chapter.title}</span><span className="text-xs text-slate-500">{chapter.duration?`${Math.floor(chapter.duration/60)} daq`:""}</span><I n="play" s={14}/></button>)}</div>:<p className="text-sm text-slate-600 mb-8">Hozircha boblar qo'shilmagan.</p>}
  {relatedBooks.length>0&&<Row title="O'xshash kitoblar" items={relatedBooks.slice(0,5)} nav={nav}/>}
 </div>;
}