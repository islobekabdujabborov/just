import React,{useEffect,useRef,useState} from "react";
import {api,getAccessToken,itemsFrom} from "../api";
import {Btn,ConfirmDialog,Cover,I,Row} from "../components/ui";
import {downloadChapterAudio,getDownloadedAudio,offlineAudioUrl,removeDownloadedAudio} from "../offlineAudio";

const PLAYBACK_SPEEDS=[0.75,1,1.25,1.5,2];
const getSavedPlaybackSpeed=()=>{
 try{
  const preferences=JSON.parse(localStorage.getItem("avobook.preferences")||"{}");
  const speed=Number(preferences.playbackSpeed);
  return PLAYBACK_SPEEDS.includes(speed)?speed:1;
 }catch{return 1;}
};
const savePlaybackSpeed=speed=>{
 let preferences={};
 try{
  const stored=JSON.parse(localStorage.getItem("avobook.preferences")||"{}");
  if(stored&&typeof stored==="object"&&!Array.isArray(stored))preferences=stored;
 }catch{}
 localStorage.setItem("avobook.preferences",JSON.stringify({...preferences,playbackSpeed:speed}));
};

export default function BookDetail({id,nav,autoPlay=false}){
 const [book,setBook]=useState(null);
 const [audiobook,setAudiobook]=useState(null);
 const [chapters,setChapters]=useState([]);
 const [relatedBooks,setRelatedBooks]=useState([]);
 const [chapterIndex,setChapterIndex]=useState(0);
 const [isLiked,setIsLiked]=useState(false);
 const [isSaved,setIsSaved]=useState(false);
 const [loading,setLoading]=useState(true);
 const [loadedBookId,setLoadedBookId]=useState(null);
 const [audioError,setAudioError]=useState("");
 const [error,setError]=useState("");
 const [bookmarks,setBookmarks]=useState([]);
 const [bookmarkNote,setBookmarkNote]=useState("");
 const [bookmarkError,setBookmarkError]=useState("");
 const [bookmarkNotice,setBookmarkNotice]=useState("");
 const [downloadedAudio,setDownloadedAudio]=useState({});
 const [downloadingAudio,setDownloadingAudio]=useState({});
 const [offlineError,setOfflineError]=useState("");
 const [isOffline,setIsOffline]=useState(()=>!navigator.onLine);
 const [premiumPrompt,setPremiumPrompt]=useState(false);
 const [playbackUrl,setPlaybackUrl]=useState("");
 const [loadingStream,setLoadingStream]=useState(false);
 const [shouldAutoPlay,setShouldAutoPlay]=useState(false);
 const [reviews,setReviews]=useState([]);
 const [reviewRating,setReviewRating]=useState(5);
 const [reviewText,setReviewText]=useState("");
 const [reviewLoading,setReviewLoading]=useState(true);
 const [reviewSaving,setReviewSaving]=useState(false);
 const [reviewError,setReviewError]=useState("");
 const [reviewNotice,setReviewNotice]=useState("");
 const [confirmTarget,setConfirmTarget]=useState(null);
 const [confirmBusy,setConfirmBusy]=useState(false);
 const [playbackSpeed,setPlaybackSpeed]=useState(getSavedPlaybackSpeed);
 const [sleepTimer,setSleepTimer]=useState("off");
 const audioRef=useRef(null);
 const savedPosition=useRef(0);
 const lastProgressSent=useRef(0);
 const pendingSeek=useRef(null);
 const sleepTimerRef=useRef(null);
 const autoPlayRequested=useRef(false);

 useEffect(()=>{
  let active=true;
  setSleepTimer("off");
  autoPlayRequested.current=false;
  setLoading(true);
  setLoadedBookId(null);
  setError("");
  setAudioError("");
  setBook(null);
  setAudiobook(null);
  setChapters([]);
  setBookmarks([]);
  setDownloadedAudio({});
  setOfflineError("");
  setPremiumPrompt(false);
  setPlaybackUrl("");
  setBookmarkNote("");
  setBookmarkError("");
  setBookmarkNotice("");
  setReviews([]);
  setReviewRating(5);
  setReviewText("");
  setReviewLoading(true);
  setReviewError("");
  setReviewNotice("");
  setChapterIndex(0);
  savedPosition.current=0;
  lastProgressSent.current=0;
  api.get(`/books/${id}/reviews/`).then(payload=>{
   if(!active)return;
   const list=itemsFrom(payload);
   setReviews(list);
   const ownReview=list.find(item=>item.is_mine);
   if(ownReview){setReviewRating(ownReview.rating);setReviewText(ownReview.text||"");}
  }).catch(reason=>{if(active)setReviewError(reason.message||"Sharhlarni yuklab bo'lmadi.");}).finally(()=>{if(active)setReviewLoading(false);});
  Promise.all([api.get(`/books/${id}/`),api.get("/books/").catch(()=>[]),api.get("/audiobooks/").catch(()=>[])]).then(async([bookResult,booksPayload,audioPayload])=>{
   if(!active)return;
   setBook(bookResult);
   setIsLiked(Boolean(bookResult.is_liked));
   setIsSaved(Boolean(bookResult.is_saved));
   setRelatedBooks(itemsFrom(booksPayload).filter(item=>String(item.id)!==String(id)));
   const match=itemsFrom(audioPayload).find(item=>String(item.book?.id)===String(id));
   if(!match){setLoadedBookId(String(id));return;}
   setAudiobook(match);
   if(getAccessToken()){
    try{
     setBookmarks(itemsFrom(await api.get(`/audiobooks/${match.id}/bookmarks/`)));
    }catch(reason){
     if(active)setBookmarkError(reason.message||"Xatcho'plarni yuklab bo'lmadi.");
    }
   }
   let parts=itemsFrom(match.chapters);
   try{parts=itemsFrom(await api.get(`/audiobooks/${match.id}/chapters/`));}catch{}
   if(!active)return;
   setChapters(parts);
   setLoadedBookId(String(id));
   getDownloadedAudio().then(entries=>{
    if(active)setDownloadedAudio(Object.fromEntries(entries.filter(entry=>entry.chapter_id).map(entry=>[entry.chapter_id,true])));
   }).catch(reason=>{if(active)setOfflineError(reason.message);});
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
   clearTimeout(sleepTimerRef.current);
  };
 },[id]);

 useEffect(()=>{
  const onOnline=()=>setIsOffline(false);
  const onOffline=()=>setIsOffline(true);
  window.addEventListener("online",onOnline);
  window.addEventListener("offline",onOffline);
  return()=>{
   window.removeEventListener("online",onOnline);
   window.removeEventListener("offline",onOffline);
  };
 },[]);

 const activeChapter=chapters[chapterIndex];
 const audioUrl=activeChapter?.audio_url||activeChapter?.audio_file||audiobook?.audio_url||audiobook?.audio_file||"";
 const hasAudio=activeChapter?activeChapter.has_audio:Boolean(audiobook?.has_audio||audioUrl);
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
 useEffect(()=>{
  const player=audioRef.current;
  if(player)player.playbackRate=playbackSpeed;
 },[playbackSpeed,playbackUrl]);
 useEffect(()=>{
  if(!shouldAutoPlay||!playbackUrl)return;
  const player=audioRef.current;
  if(!player)return;
  player.play().then(()=>setAudioError("")).catch(()=>setAudioError("Ijro boshlanmadi. Audio pleerdagi Play tugmasini bosing."));
  setShouldAutoPlay(false);
 },[playbackUrl,shouldAutoPlay]);
 const playAudio=async()=>{
  if(activeChapter?.locked){setPremiumPrompt(true);return;}
  if(!hasAudio){setAudioError("Bu kitob uchun audio hali yuklanmagan.");return;}
  if(loadingStream)return;
  setAudioError("");
  if(activeChapter&&isOffline&&downloadedAudio[activeChapter.id]){
   setPlaybackUrl(offlineAudioUrl(activeChapter.id));
   setShouldAutoPlay(true);
   return;
  }
  setLoadingStream(true);
  try{
   const stream=activeChapter
    ?await api.get(`/chapters/${activeChapter.id}/stream/`)
    :await api.get(`/audiobooks/${audiobook.id}/stream/`);
   setPlaybackUrl(stream.url);
   setShouldAutoPlay(true);
  }catch(reason){
   if(reason.message?.toLowerCase().includes("premium"))setPremiumPrompt(true);
   else if(activeChapter&&isOffline&&downloadedAudio[activeChapter.id]){
    setPlaybackUrl(offlineAudioUrl(activeChapter.id));
    setShouldAutoPlay(true);
   }else setAudioError(reason.message||"Audio oqimini ochib bo'lmadi.");
  }finally{setLoadingStream(false);}
 };
 useEffect(()=>{
  if(!autoPlay||loading||loadedBookId!==String(id)||autoPlayRequested.current||!audiobook||(chapters.length===0&&!audiobook.has_audio))return;
  autoPlayRequested.current=true;
  setChapterIndex(0);
  const firstChapter=chapters[0];
  if(firstChapter?.locked){setPremiumPrompt(true);return;}
  setLoadingStream(true);
  const streamRequest=firstChapter
   ?api.get(`/chapters/${firstChapter.id}/stream/`)
   :api.get(`/audiobooks/${audiobook.id}/stream/`);
  streamRequest.then(stream=>{setPlaybackUrl(stream.url);setShouldAutoPlay(true);})
   .catch(reason=>{if(reason.message?.toLowerCase().includes("premium"))setPremiumPrompt(true);else setAudioError(reason.message||"Audio oqimini ochib bo'lmadi.");})
   .finally(()=>setLoadingStream(false));
 },[autoPlay,loading,loadedBookId,id,audiobook,chapters]);
 const seekToBookmark=bookmark=>{
  setBookmarkError("");
  if(bookmark.chapter){
   const targetIndex=chapters.findIndex(chapter=>String(chapter.id)===String(bookmark.chapter));
   if(targetIndex>=0&&targetIndex!==chapterIndex){
    pendingSeek.current=bookmark.position;
    setChapter(targetIndex);
    return;
   }
  }
  const player=audioRef.current;
  if(!player)return;
  if(player.readyState>=1)player.currentTime=bookmark.position;
  else pendingSeek.current=bookmark.position;
 };
 const addBookmark=async()=>{
  if(!getAccessToken()){nav("/login");return;}
  const player=audioRef.current;
  if(!audiobook||!player){setBookmarkError("Xatcho'p qo'shish uchun audio mavjud emas.");return;}
  setBookmarkError("");
  setBookmarkNotice("");
  try{
   const bookmark=await api.post(`/audiobooks/${audiobook.id}/bookmarks/`,{
    chapter:activeChapter?.id||null,
    position:Math.floor(player.currentTime||0),
    note:bookmarkNote.trim(),
   });
   setBookmarks(current=>[bookmark,...current]);
   setBookmarkNote("");
   setBookmarkNotice("Xatcho'p saqlandi.");
  }catch(reason){setBookmarkError(reason.message||"Xatcho'pni saqlab bo'lmadi.");}
 };
 const toggleChapterDownload=async chapter=>{
  if(chapter.locked){setPremiumPrompt(true);return;}
  if(!chapter.has_audio)return;
  setOfflineError("");
  setDownloadingAudio(current=>({...current,[chapter.id]:true}));
  try{
   if(downloadedAudio[chapter.id]){
    await removeDownloadedAudio(chapter.id);
    setDownloadedAudio(current=>{const next={...current};delete next[chapter.id];return next;});
   }else{
    const stream=await api.get(`/chapters/${chapter.id}/stream/`);
    await downloadChapterAudio(chapter.id,stream.url);
    setDownloadedAudio(current=>({...current,[chapter.id]:true}));
   }
  }catch(reason){
   if(reason.message?.toLowerCase().includes("premium"))setPremiumPrompt(true);
   else setOfflineError(reason.message||"Offline audio amalini bajarib bo'lmadi.");
  }
  finally{setDownloadingAudio(current=>({...current,[chapter.id]:false}));}
 };
 const updateDisplayedRating=nextReviews=>{
  const rating=nextReviews.length?(nextReviews.reduce((sum,review)=>sum+Number(review.rating),0)/nextReviews.length).toFixed(1):"0.0";
  setBook(current=>current?{...current,rating,r:rating}:current);
 };
 const submitReview=async event=>{
  event.preventDefault();
  if(!getAccessToken()){nav("/login");return;}
  setReviewSaving(true);
  setReviewError("");
  setReviewNotice("");
  try{
   const ownReview=reviews.find(item=>item.is_mine);
   const review=ownReview
    ?await api.patch(`/reviews/${ownReview.id}/`,{rating:reviewRating,text:reviewText.trim()})
    :await api.post(`/books/${id}/reviews/`,{rating:reviewRating,text:reviewText.trim()});
   const nextReviews=ownReview
    ?reviews.map(item=>item.id===review.id?review:item)
    :[review,...reviews];
   setReviews(nextReviews);
   updateDisplayedRating(nextReviews);
   setReviewNotice(ownReview?"Sharhingiz yangilandi.":"Sharhingiz qo'shildi.");
  }catch(reason){setReviewError(reason.message||"Sharhni saqlab bo'lmadi.");}
  finally{setReviewSaving(false);}
 };
 const deleteReview=async()=>{
  const ownReview=reviews.find(item=>item.is_mine);
  if(!ownReview)return;
  setConfirmBusy(true);
  setReviewError("");
  setReviewNotice("");
  try{
   await api.delete(`/reviews/${ownReview.id}/`);
   const nextReviews=reviews.filter(item=>item.id!==ownReview.id);
   setReviews(nextReviews);
   updateDisplayedRating(nextReviews);
   setReviewRating(5);
   setReviewText("");
   setReviewNotice("Sharhingiz o'chirildi.");
   setConfirmTarget(null);
  }catch{setReviewError("Sharhni o'chirib bo'lmadi. Qayta urinib ko'ring.");setConfirmTarget(null);}
  finally{setConfirmBusy(false);}
 };
 const deleteBookmark=async bookmark=>{
  setConfirmBusy(true);
  setBookmarkError("");
  setBookmarkNotice("");
  try{
   await api.delete(`/bookmarks/${bookmark.id}/`);
   setBookmarks(current=>current.filter(item=>item.id!==bookmark.id));
   setBookmarkNotice("Xatcho'p o'chirildi.");
   setConfirmTarget(null);
  }catch{setBookmarkError("Xatcho'pni o'chirib bo'lmadi. Qayta urinib ko'ring.");setConfirmTarget(null);}
  finally{setConfirmBusy(false);}
 };
 const setChapter=index=>{
  if(chapters[index]?.locked){setPremiumPrompt(true);return;}
  setChapterIndex(index);
  setPlaybackUrl("");
  setShouldAutoPlay(false);
  savedPosition.current=0;
  setAudioError("");
 };
 useEffect(()=>{
  if(audioRef.current)audioRef.current.playbackRate=playbackSpeed;
  savePlaybackSpeed(playbackSpeed);
 },[playbackSpeed,playbackUrl]);
 useEffect(()=>{
  clearTimeout(sleepTimerRef.current);
  if(sleepTimer!=="off"&&sleepTimer!=="chapter"){
   sleepTimerRef.current=setTimeout(()=>{
    audioRef.current?.pause();
    setSleepTimer("off");
   },Number(sleepTimer)*60*1000);
  }
  return()=>clearTimeout(sleepTimerRef.current);
 },[sleepTimer]);
 const handleChapterEnd=()=>{
  saveProgress(true);
  if(sleepTimer==="chapter"){setSleepTimer("off");return;}
  if(chapterIndex<chapters.length-1)setChapter(chapterIndex+1);
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
    {audiobook?.access==="premium"&&<span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800"><I n="lock" s={13}/>Premium</span>}
    <h1 className="text-3xl sm:text-4xl font-extrabold mt-3 break-words">{title}</h1>
    <p className="text-slate-600">{author}</p>
    <div className="flex flex-wrap gap-4 text-sm text-slate-600 my-3"><span className="flex items-center gap-1"><I n="star" f={1} s={15}/>{book.r||book.rating||"Baholanmagan"}</span><span className="flex items-center gap-1"><I n="clock" s={15}/>{book.d||"Davomiyligi noma'lum"}</span></div>
    <p className="max-w-xl text-sm text-slate-700 whitespace-pre-wrap">{description}</p>
    <div className="flex flex-wrap gap-3 mt-5">
     <Btn onClick={playAudio} disabled={loadingStream} cn="px-6 py-3 flex items-center gap-2"><I n="play" f={1} s={16}/>{loadingStream?"Yuklanmoqda...":"Tinglash"}</Btn>
     <Btn v="g" onClick={()=>toggleBookInteraction("save")} aria-label={isSaved?"Saqlanganlardan olib tashlash":"Saqlash"} aria-pressed={isSaved} cn="px-4 py-3"><I n="save" f={isSaved?1:0}/></Btn>
     <Btn v="g" onClick={()=>toggleBookInteraction("like")} aria-label={isLiked?"Yoqtirishdan olib tashlash":"Yoqtirish"} aria-pressed={isLiked} cn="px-4 py-3"><I n="heart" f={isLiked?1:0}/></Btn>
     <Btn v="g" onClick={()=>nav(`/create?book=${id}&audio=1`)} cn="px-4 py-3">Shu kitobdan reel yaratish</Btn>
    </div>
   </div>
  </div>
  {error&&<p role="alert" className="text-sm text-rose-700 mb-4">{error}</p>}
  <section className="glass rounded-2xl p-4 sm:p-5 mb-8" aria-labelledby="reviews-title">
   <h2 id="reviews-title" className="font-extrabold mb-3">Kitobxonlar bahosi va sharhlari</h2>
   {getAccessToken()?<form onSubmit={submitReview} className="mb-5 rounded-xl border border-black/10 p-4">
    <p className="text-sm font-semibold mb-2">{reviews.some(item=>item.is_mine)?"Sharhingizni yangilang":"Kitobga baho bering"}</p>
    <div className="flex items-center gap-1 mb-3" role="group" aria-label="Baho, 1 dan 5 gacha">
     {[1,2,3,4,5].map(value=><button key={value} type="button" onClick={()=>setReviewRating(value)} aria-label={`${value} yulduz`} aria-pressed={reviewRating===value} className={`p-1 ${value<=reviewRating?"text-amber-500":"text-slate-300"}`}><I n="star" f={value<=reviewRating?1:0} s={23}/></button>)}
    </div>
    <label htmlFor="review-text" className="block text-sm font-medium mb-2">Sharh (ixtiyoriy)</label>
    <textarea id="review-text" value={reviewText} onChange={event=>setReviewText(event.target.value)} maxLength={2000} rows={3} placeholder="Kitob haqidagi fikringiz" className="w-full rounded-xl border border-black/15 bg-white px-3 py-2 text-sm"/>
    <div className="mt-3 flex flex-wrap gap-2">
     <Btn type="submit" disabled={reviewSaving||reviewLoading} cn="px-4 py-2">{reviewSaving?"Saqlanmoqda...":reviews.some(item=>item.is_mine)?"Sharhni yangilash":"Sharh yuborish"}</Btn>
     {reviews.some(item=>item.is_mine)&&<Btn type="button" v="g" disabled={reviewSaving} onClick={()=>setConfirmTarget({title:"Sharhni o'chirish",message:"Sharhingizni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",onConfirm:deleteReview})} cn="px-4 py-2">Sharhni o'chirish</Btn>}
    </div>
   </form>:<p className="mb-4 text-sm text-slate-600">Baho berish va sharh yozish uchun <button type="button" onClick={()=>nav("/login")} className="font-bold underline">tizimga kiring</button>.</p>}
   {reviewError&&<p role="alert" className="text-sm text-rose-700 mb-3">{reviewError}</p>}
   {reviewNotice&&<p role="status" className="text-sm text-emerald-700 mb-3">{reviewNotice}</p>}
   {reviewLoading?<p role="status" className="text-sm text-slate-600">Sharhlar yuklanmoqda...</p>:reviews.length?<div className="divide-y divide-black/10">{reviews.map(review=><article key={review.id} className="py-3">
    <div className="flex items-center justify-between gap-3">
     <p className="text-sm font-bold">{review.user_name||"Kitobxon"}{review.is_mine?" (siz)":""}</p>
     <span className="flex items-center gap-1 text-sm font-semibold text-amber-600"><I n="star" f={1} s={15}/>{review.rating}/5</span>
    </div>
    {review.text&&<p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{review.text}</p>}
   </article>)}</div>:<p className="text-sm text-slate-600">Hozircha sharh yo'q. Birinchi bo'lib fikringizni yozing.</p>}
  </section>
  <section className="glass rounded-2xl p-4 sm:p-5 mb-8" aria-label="Audio player">
   {isOffline&&<p role="status" className="mb-3 text-sm font-semibold text-amber-700">Offline rejim</p>}
   {activeChapter&&downloadedAudio[activeChapter.id]&&<p role="status" className="mb-3 text-sm font-semibold text-emerald-700">Offline mavjud</p>}
   <div className="flex flex-col sm:flex-row sm:items-center gap-3">
    <div className="flex-1 min-w-0"><p className="text-sm font-bold truncate">{activeChapter?.title||title}</p>
     <audio key={activeChapter?.id||audiobook?.id||id} ref={audioRef} controls={Boolean(playbackUrl)} preload="metadata" src={playbackUrl||undefined} onLoadedMetadata={event=>{if(pendingSeek.current!==null){event.currentTarget.currentTime=pendingSeek.current;pendingSeek.current=null;}else if(savedPosition.current){event.currentTarget.currentTime=savedPosition.current;savedPosition.current=0;}}} onTimeUpdate={()=>saveProgress()} onPause={()=>saveProgress(true)} onEnded={handleChapterEnd} onError={()=>setAudioError("Audio faylni yuklab bo'lmadi.")} className="mt-2 h-10 w-full"/>
    </div>
    <div className="flex gap-2 justify-end">
     <Btn v="g" disabled={!chapters.length||chapterIndex===0} aria-label="Oldingi bob" onClick={()=>setChapter(chapterIndex-1)} cn="px-3 py-2"><I n="up" s={18}/></Btn>
     <Btn v="g" disabled={!chapters.length||chapterIndex>=chapters.length-1} aria-label="Keyingi bob" onClick={()=>setChapter(chapterIndex+1)} cn="px-3 py-2"><I n="up" s={18}/></Btn>
    </div>
   </div>
   <div className="mt-4 flex flex-wrap items-center gap-4">
    <label className="flex items-center gap-2 text-sm font-medium">
     <span>Tezlik</span>
     <select aria-label="Ijro tezligi" value={playbackSpeed} onChange={event=>setPlaybackSpeed(Number(event.target.value))} className="rounded-lg border border-black/15 bg-white px-2 py-1.5">
      {PLAYBACK_SPEEDS.map(speed=><option key={speed} value={speed}>{speed}x</option>)}
     </select>
    </label>
    <label className="flex items-center gap-2 text-sm font-medium">
     <span>Uyqu taymeri</span>
     <select aria-label="Uyqu taymeri" value={sleepTimer} onChange={event=>setSleepTimer(event.target.value)} className="rounded-lg border border-black/15 bg-white px-2 py-1.5">
      <option value="off">O'chirilgan</option>
      <option value="15">15 daqiqa</option>
      <option value="30">30 daqiqa</option>
      <option value="45">45 daqiqa</option>
      <option value="60">60 daqiqa</option>
      <option value="chapter">Bob oxirida</option>
     </select>
    </label>
   </div>
   {getAccessToken()?<div className="mt-4 flex flex-col sm:flex-row sm:items-end gap-2">
    <label htmlFor="bookmark-note" className="flex-1 text-sm font-medium">Xatcho'p qaydi (ixtiyoriy)
     <textarea id="bookmark-note" value={bookmarkNote} onChange={event=>setBookmarkNote(event.target.value)} maxLength={500} rows={2} placeholder="Bu joy haqida qayd yozing" className="mt-1 w-full rounded-xl border border-black/15 bg-white px-3 py-2 text-sm"/>
    </label>
    <Btn type="button" onClick={addBookmark} disabled={!audiobook||!hasAudio||activeChapter?.locked} cn="px-4 py-2">Xatcho'p qo'shish</Btn>
   </div>:<p className="mt-3 text-sm text-slate-600">Xatcho'p qo'shish uchun <button type="button" onClick={()=>nav("/login")} className="font-bold underline">tizimga kiring</button>.</p>}
   {!hasAudio&&!audioError&&<p className="text-sm text-slate-600 mt-2">Audio hali mavjud emas.</p>}
   {audioError&&<p role="alert" className="text-sm text-rose-700 mt-2">{audioError}</p>}
   {bookmarkError&&<p role="alert" className="text-sm text-rose-700 mt-2">{bookmarkError}</p>}
   {bookmarkNotice&&<p role="status" className="text-sm text-emerald-700 mt-2">{bookmarkNotice}</p>}
   {offlineError&&<p role="alert" className="text-sm text-rose-700 mt-2">{offlineError}</p>}
  </section>
  <section className="glass rounded-2xl p-4 sm:p-5 mb-8" aria-labelledby="bookmarks-title">
   <h2 id="bookmarks-title" className="font-extrabold mb-3">Xatcho'plar va qaydlar</h2>
   {bookmarks.length?<div className="divide-y divide-black/10">{bookmarks.map(bookmark=>{
    const chapter=chapters.find(part=>String(part.id)===String(bookmark.chapter));
    const minutes=Math.floor(bookmark.position/60);
    const seconds=String(bookmark.position%60).padStart(2,"0");
    return <div key={bookmark.id} className="flex items-center gap-2 px-2 py-2">
     <button type="button" onClick={()=>seekToBookmark(bookmark)} className="min-w-0 flex-1 rounded-lg py-1 text-left hover:bg-neutral-100">
      <span className="flex items-center justify-between gap-3 text-sm font-semibold"><span>{chapter?.title||"Audiokitob"}</span><span className="shrink-0 text-slate-600">{minutes}:{seconds}</span></span>
      {bookmark.note&&<span className="mt-1 block whitespace-pre-wrap text-sm text-slate-600">{bookmark.note}</span>}
     </button>
     {getAccessToken()&&<button type="button" aria-label="Xatcho'pni o'chirish" onClick={()=>setConfirmTarget({title:"Xatcho'pni o'chirish",message:"Xatcho'pni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",onConfirm:()=>deleteBookmark(bookmark)})} className="shrink-0 rounded-lg px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50">O'chirish</button>}
    </div>;
   })}</div>:<p className="text-sm text-slate-600">Hozircha xatcho'p qo'shilmagan.</p>}
  </section>
  <h2 className="font-extrabold mb-3">Boblar</h2>
  {chapters.length?<div className="glass rounded-2xl divide-y divide-black/10 mb-8">{chapters.map((chapter,index)=>{
   const isDownloaded=Boolean(downloadedAudio[chapter.id]);
   return <div key={chapter.id} className={`flex items-center gap-2 px-3 py-2 ${index===chapterIndex?"bg-neutral-50":""}`}>
    <button type="button" onClick={()=>setChapter(index)} aria-current={index===chapterIndex?"true":undefined} className={`flex min-w-0 flex-1 items-center gap-3 py-1 text-left hover:bg-neutral-100 ${index===chapterIndex?"font-bold":""}`}><span className="text-xs w-5 text-slate-500">{index+1}</span><span className="flex-1 min-w-0 text-sm truncate">{chapter.title}</span>{chapter.is_free_preview&&<span className="shrink-0 text-xs font-semibold text-emerald-700">Bepul namuna</span>}<span className="text-xs text-slate-500">{chapter.duration?`${Math.floor(chapter.duration/60)} daq`:""}</span>{chapter.locked?<I n="lock" s={16}/>:<I n="play" s={14}/>}</button>
    {isDownloaded&&<span className="shrink-0 text-xs font-semibold text-emerald-700">Offline</span>}
    {chapter.locked?<button type="button" onClick={()=>setPremiumPrompt(true)} className="shrink-0 rounded-lg border border-amber-300 px-2 py-1.5 text-xs font-semibold text-amber-800">Premium kerak</button>:<button type="button" onClick={()=>toggleChapterDownload(chapter)} disabled={!chapter.has_audio||downloadingAudio[chapter.id]} aria-label={isDownloaded?`${chapter.title} offline nusxasini o'chirish`:`${chapter.title} ni yuklab olish`} className="shrink-0 rounded-lg border border-black/10 px-2 py-1.5 text-xs font-semibold disabled:opacity-50">{downloadingAudio[chapter.id]?"Kutilmoqda...":isDownloaded?"O'chirish":"Yuklab olish"}</button>}
   </div>;
  })}</div>:<p className="text-sm text-slate-600 mb-8">Hozircha boblar qo'shilmagan.</p>}
  {relatedBooks.length>0&&<Row title="O'xshash kitoblar" items={relatedBooks.slice(0,5)} nav={nav}/>}
  {premiumPrompt&&<div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" onClick={()=>setPremiumPrompt(false)}>
   <section role="dialog" aria-modal="true" aria-labelledby="premium-title" onClick={event=>event.stopPropagation()} className="w-full max-w-md rounded-2xl bg-white p-6 text-black shadow-2xl">
    <div className="mb-3 flex items-center justify-between"><h2 id="premium-title" className="flex items-center gap-2 text-xl font-extrabold"><I n="lock" s={20}/>Premium kerak</h2><button type="button" onClick={()=>setPremiumPrompt(false)} aria-label="Yopish"><I n="x" s={20}/></button></div>
    <p className="text-sm text-slate-600">Bu bobni tinglash uchun faol Premium obuna kerak. Hozircha obuna va to'lov xizmati mavjud emas.</p>
    <Btn type="button" disabled cn="mt-5 w-full py-3">Obuna bo'lish — tez orada</Btn>
   </section>
  </div>}
  <ConfirmDialog open={Boolean(confirmTarget)} title={confirmTarget?.title} message={confirmTarget?.message} loading={confirmBusy} onConfirm={confirmTarget?.onConfirm} onCancel={()=>setConfirmTarget(null)}/>
 </div>;
}