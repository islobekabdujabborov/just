import React,{useEffect,useRef,useState} from "react";
import {api,itemsFrom,uploadWithProgress} from "../api";
import {Btn,Drop,Field} from "../components/ui";

const GENRES=["Roman","Detektiv","Fantastika","Biznes","Psixologiya","Tarix","Ta'lim","Sarguzasht","She'r"];
const AUDIO_EXTENSIONS=["mp3","m4a","wav","ogg"];
const MAX_FILE_SIZE=100*1024*1024;

function useObjectUrl(file){
 const [url,setUrl]=useState("");
 useEffect(()=>{
  if(!file){setUrl("");return;}
  const objectUrl=URL.createObjectURL(file);
  setUrl(objectUrl);
  return()=>URL.revokeObjectURL(objectUrl);
 },[file]);
 return url;
}

function formatSize(size){
 return size<1024*1024?`${(size/1024).toFixed(0)} KB`:`${(size/1024/1024).toFixed(1)} MB`;
}

function AudioFilesSection({files,setFiles,access,setAccess,disabled,onError}){
 const inputRef=useRef(null);
 const [dragging,setDragging]=useState(false);
 const appendFiles=selected=>{
  const accepted=[];
  let message="";
  for(const file of selected){
   const extension=file.name.split(".").pop()?.toLowerCase();
   if(!AUDIO_EXTENSIONS.includes(extension)){message=`${file.name}: audio MP3, M4A, WAV yoki OGG bo'lishi kerak.`;continue;}
   if(file.size>MAX_FILE_SIZE){message=`${file.name}: audio fayl 100 MB dan oshmasligi kerak.`;continue;}
   if(files.length+accepted.length>=30){message="Bir martada ko'pi bilan 30 ta bob yuklash mumkin.";break;}
   accepted.push({file,title:file.name.replace(/\.[^.]+$/,"")||"Yangi bob",preview:false});
  }
  if(message)onError(message);
  if(accepted.length)setFiles(previous=>[...previous,...accepted]);
 };
 const updateFile=(index,updates)=>setFiles(previous=>previous.map((item,itemIndex)=>itemIndex===index?{...item,...updates}:item));
 const moveFile=(index,offset)=>setFiles(previous=>{
  const target=index+offset;
  if(target<0||target>=previous.length)return previous;
  const next=[...previous];
  [next[index],next[target]]=[next[target],next[index]];
  return next;
 });
 const totalSize=files.reduce((sum,item)=>sum+item.file.size,0);
 return <section className="mt-5 rounded-2xl border border-black/10 p-4">
  <div className="flex flex-wrap items-center justify-between gap-3">
   <div><h3 className="font-bold">Audio kitob qo'shish</h3><p className="text-xs text-neutral-600">Har bir audio fayl alohida bob bo'ladi.</p></div>
   <label className="flex items-center gap-2 text-sm font-semibold">
    <span>Ochiq / Premium</span>
    <select value={access} onChange={event=>setAccess(event.target.value)} disabled={disabled} className="rounded-lg border border-black/15 bg-white px-3 py-2 text-black">
     <option value="free">Ochiq</option><option value="premium">Premium</option>
    </select>
   </label>
  </div>
  <div
   onDragOver={event=>{event.preventDefault();setDragging(true);}}
   onDragLeave={()=>setDragging(false)}
   onDrop={event=>{event.preventDefault();setDragging(false);appendFiles(Array.from(event.dataTransfer.files));}}
   className={`mt-4 rounded-xl border-2 border-dashed p-5 text-center ${dragging?"border-black bg-neutral-100":"border-black/20"}`}
  >
   <p className="mb-2 text-sm text-neutral-700">Audio fayllarni shu yerga tashlang yoki tanlang</p>
   <input ref={inputRef} type="file" multiple accept=".mp3,.m4a,.wav,.ogg,audio/mpeg,audio/mp4,audio/wav,audio/ogg" disabled={disabled} onChange={event=>{appendFiles(Array.from(event.target.files||[]));event.target.value="";}} className="block w-full text-sm text-neutral-700"/>
  </div>
  {files.length>0&&<div className="mt-4 space-y-3">
   {files.map((item,index)=><div key={`${item.file.name}-${item.file.lastModified}-${index}`} className="grid gap-3 rounded-xl bg-neutral-50 p-3 md:grid-cols-[1fr_auto]">
    <div className="min-w-0">
     <p className="truncate text-xs text-neutral-600">{item.file.name} · {formatSize(item.file.size)}</p>
     <input aria-label={`${index+1}-bob nomi`} value={item.title} disabled={disabled} maxLength={200} onChange={event=>updateFile(index,{title:event.target.value})} className="mt-2 w-full rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-black" placeholder={`${index+1}-bob`}/>
     <label className="mt-2 flex items-center gap-2 text-xs text-neutral-700">
      <input type="checkbox" checked={item.preview} disabled={disabled} onChange={event=>updateFile(index,{preview:event.target.checked})}/>
      Bepul tinglash (preview)
     </label>
    </div>
    <div className="flex items-center gap-2 md:items-start">
     <button type="button" aria-label="Bobni yuqoriga ko'chirish" disabled={disabled||index===0} onClick={()=>moveFile(index,-1)} className="rounded-lg border border-black/15 px-3 py-2 disabled:opacity-40">↑</button>
     <button type="button" aria-label="Bobni pastga ko'chirish" disabled={disabled||index===files.length-1} onClick={()=>moveFile(index,1)} className="rounded-lg border border-black/15 px-3 py-2 disabled:opacity-40">↓</button>
     <button type="button" disabled={disabled} onClick={()=>setFiles(previous=>previous.filter((_,fileIndex)=>fileIndex!==index))} className="rounded-lg border border-rose-200 px-3 py-2 text-rose-700 disabled:opacity-40">O'chirish</button>
    </div>
   </div>)}
   <p className="text-right text-xs font-semibold text-neutral-600">{files.length} bob · jami {formatSize(totalSize)}</p>
  </div>}
 </section>;
}

export default function Create({nav,bookId:contextBookId,audioEnabled:contextAudioEnabled}){
 const [mode,setMode]=useState("reel");
 const [values,setValues]=useState({title:"",author:"",genre:"Roman",description:"",caption:""});
 const [video,setVideo]=useState(null);
 const [cover,setCover]=useState(null);
 const [audioFiles,setAudioFiles]=useState([]);
 const [access,setAccess]=useState("free");
 const [audioEnabled,setAudioEnabled]=useState(Boolean(contextAudioEnabled));
 const [bookSource,setBookSource]=useState(contextBookId?"existing":"new");
 const [selectedBookId,setSelectedBookId]=useState(contextBookId?String(contextBookId):"");
 const [bookSearch,setBookSearch]=useState("");
 const [books,setBooks]=useState([]);
 const [bookLoading,setBookLoading]=useState(false);
 const [bookError,setBookError]=useState("");
 const [currentUserId,setCurrentUserId]=useState(null);
 const [error,setError]=useState("");
 const [success,setSuccess]=useState("");
 const [submitting,setSubmitting]=useState(false);
 const [uploadProgress,setUploadProgress]=useState(0);
 const activeUpload=useRef(null);
 const videoPreview=useObjectUrl(video);
 const coverPreview=useObjectUrl(cover);

 useEffect(()=>{
  let active=true;
  setBookLoading(true);
  api.get("/auth/me/").then(async user=>{
   if(active)setCurrentUserId(user.id);
   const ownBooks=[];
   let page=1;
   let next=true;
   while(next){
    const payload=await api.get(`/books/?page=${page}`);
    ownBooks.push(...itemsFrom(payload).filter(book=>String(book.owner_id)===String(user.id)));
    next=Boolean(payload?.next);
    page+=1;
   }
   if(active)setBooks(ownBooks);
  }).catch(reason=>{if(active)setBookError(reason.message||"Kitoblar ro'yxatini yuklab bo'lmadi.");}).finally(()=>{if(active)setBookLoading(false);});
  return()=>{active=false;};
 },[]);

 useEffect(()=>{
  if(contextBookId){setBookSource("existing");setSelectedBookId(String(contextBookId));}
  if(contextAudioEnabled)setAudioEnabled(true);
 },[contextBookId,contextAudioEnabled]);

 const update=event=>{
  const {name,value}=event.target;
  setValues(previous=>({...previous,[name]:value}));
 };
 const reset=()=>{
  setValues({title:"",author:"",genre:"Roman",description:"",caption:""});
  setVideo(null);
  setCover(null);
  setAudioFiles([]);
  setAccess("free");
  setBookSource("new");
  setSelectedBookId("");
  setBookSearch("");
  setAudioEnabled(false);
  setUploadProgress(0);
 };
 const selectedBook=books.find(book=>String(book.id)===selectedBookId);
 const filteredBooks=books.filter(book=>`${book.title} ${book.author?.name||""}`.toLowerCase().includes(bookSearch.toLowerCase()));

 const submit=async event=>{
  event.preventDefault();
  setError("");
  setSuccess("");
  const isExisting=bookSource==="existing";
  if(isExisting&&!selectedBookId){setError("Mavjud kitobni tanlang.");return;}
  if(!isExisting&&(!values.title.trim()||!values.author.trim())){setError("Kitob nomi va muallifini kiriting.");return;}
  if(mode==="reel"&&!video){setError("Reel uchun video tanlang.");return;}
  if(mode==="book"&&!audioFiles.length){setError("Audiokitob uchun kamida bitta audio fayl tanlang.");return;}
  if(audioEnabled&&mode==="reel"&&audioFiles.some(item=>!item.title.trim())){setError("Har bir audio bobga nom kiriting.");return;}
  if(mode==="book"&&audioFiles.some(item=>!item.title.trim())){setError("Har bir audio bobga nom kiriting.");return;}
  const extension=file=>file?.name.split(".").pop()?.toLowerCase()||"";
  if(cover&&(!["jpg","jpeg","png","webp"].includes(extension(cover))||cover.size>8*1024*1024)){setError("Muqova JPG, PNG yoki WebP bo'lishi va 8 MB dan oshmasligi kerak.");return;}
  if(video&&(!["mp4","mov","webm"].includes(extension(video))||video.size>MAX_FILE_SIZE)){setError("Video MP4, MOV yoki WebM bo'lishi va 100 MB dan oshmasligi kerak.");return;}
  if(audioFiles.some(item=>!AUDIO_EXTENSIONS.includes(extension(item.file))||item.file.size>MAX_FILE_SIZE)){setError("Audio MP3, M4A, WAV yoki OGG bo'lishi va har biri 100 MB dan oshmasligi kerak.");return;}

  const bookData=payload=>{
   if(isExisting)payload.append("book_id",selectedBookId);
   else{
    payload.append("title",values.title.trim());
    payload.append("author_name",values.author.trim());
    payload.append("genre",values.genre);
    payload.append("description",values.description||"");
    payload.append("language","uz");
    if(cover)payload.append("cover",cover);
   }
  };
  try{
   setSubmitting(true);
   if(mode==="reel"){
    const payload=new FormData();
    payload.append("video",video);
    payload.append("caption",values.caption||"");
    bookData(payload);
    if(audioEnabled){
     payload.append("access",access);
     audioFiles.forEach(item=>{
      payload.append("audio_files",item.file);
      payload.append("chapter_titles",item.title.trim());
      payload.append("chapter_free_preview",item.preview?"true":"false");
     });
    }
    const upload=uploadWithProgress("/reels/compose/",payload,setUploadProgress);
    activeUpload.current=upload;
    const created=await upload.promise;
    activeUpload.current=null;
    setSuccess("Reel muvaffaqiyatli joylandi.");
    const destination=created.book?.id?`/books/${created.book.id}${created.book.has_audio?"?play=1":""}`:"/";
    reset();
    nav(destination);
   }else{
    let targetBookId=selectedBookId;
    if(!isExisting){
     const payload=new FormData();
     bookData(payload);
     targetBookId=(await api.post("/books/",payload)).id;
    }
    const audioPayload=await api.get("/audiobooks/");
    const existingAudiobook=itemsFrom(audioPayload).find(item=>String(item.book?.id)===String(targetBookId));
    let audiobook;
    let nextOrder=1;
    if(existingAudiobook){
     if(String(existingAudiobook.created_by)!==String(currentUserId))throw new Error("Bu kitobning audiokitobini tahrirlash huquqingiz yo'q.");
     audiobook=existingAudiobook;
     nextOrder=Math.max(0,...itemsFrom(existingAudiobook.chapters).map(chapter=>Number(chapter.order)||0))+1;
     await api.patch(`/audiobooks/${audiobook.id}/`,{access});
    }else audiobook=await api.post("/audiobooks/",{book_id:targetBookId,access});
    for(let index=0;index<audioFiles.length;index+=1){
     const item=audioFiles[index];
     const payload=new FormData();
     payload.append("title",item.title.trim()||`${index+1}-bob`);
     payload.append("audio_file",item.file);
     payload.append("order",String(nextOrder+index));
     payload.append("is_free_preview",String(item.preview));
     await api.post(`/audiobooks/${audiobook.id}/chapters/`,payload);
    }
    setSuccess("Audiokitob va boblar saqlandi.");
    reset();
    window.setTimeout(()=>nav(`/books/${targetBookId}`),500);
   }
  }catch(reason){
   activeUpload.current=null;
   if(reason.name==="AbortError")setError("Yuklash bekor qilindi. Formadagi ma'lumotlar saqlandi.");
   else setError(reason.message||"Yuklashda xatolik yuz berdi.");
  }finally{
   setSubmitting(false);
  }
 };

 const ownBookOptions=<div className="mt-4 rounded-2xl border border-black/10 p-4">
  <Field l="Mavjud kitobni qidirish" ph="Kitob yoki muallif nomi" value={bookSearch} onChange={event=>setBookSearch(event.target.value)}/>
  <select aria-label="Mavjud kitobni tanlash" value={selectedBookId} onChange={event=>setSelectedBookId(event.target.value)} className="mt-3 w-full rounded-xl border border-black/15 bg-white px-4 py-3 text-black">
   <option value="">Kitobni tanlang</option>
   {filteredBooks.map(book=><option key={book.id} value={book.id}>{book.title} — {book.author?.name||"Muallif ko'rsatilmagan"}</option>)}
  </select>
  {selectedBook&&<p className="mt-2 text-xs text-neutral-600">Tanlangan: {selectedBook.title}</p>}
  {bookLoading&&<p className="mt-2 text-xs text-neutral-600">Kitoblar yuklanmoqda...</p>}
  {bookError&&<p role="alert" className="mt-2 text-xs text-rose-700">{bookError}</p>}
  {!bookLoading&&!books.length&&!bookError&&<p className="mt-2 text-xs text-neutral-600">Sizda hali kitob yo'q. “Yangi kitob”ni tanlang.</p>}
 </div>;

 return <div className="mx-auto max-w-3xl">
  <h1 className="mb-5 text-3xl font-extrabold">Yaratish</h1>
  <div className="mb-6 flex flex-wrap gap-2">
   <Btn disabled={submitting} cn={`px-5 py-2 text-sm ${mode==="reel"?"":"opacity-75"}`} on={()=>setMode("reel")}>Reel yaratish</Btn>
   <Btn v="g" disabled={submitting} cn={`px-5 py-2 text-sm ${mode==="book"?"":"opacity-75"}`} on={()=>setMode("book")}>Audio kitob yuklash</Btn>
  </div>
  <form onSubmit={submit} className="space-y-4">
   {mode==="reel"&&<div className="glass rounded-3xl p-5">
    <Drop l="Video yuklash (MP4, MOV yoki WebM)" accept=".mp4,.mov,.webm,video/mp4,video/webm,video/quicktime" onChange={event=>setVideo(event.target.files?.[0]||null)}/>
    {videoPreview&&<video src={videoPreview} controls muted playsInline preload="metadata" className="mt-4 max-h-72 w-full rounded-xl bg-black object-contain" aria-label="Tanlangan video ko'rinishi"/>}
    <label className="mt-4 block"><span className="text-xs text-neutral-600">Reel izohi</span><textarea name="caption" rows={2} value={values.caption} onChange={update} className="mt-1 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-black outline-none"/></label>
   </div>}
   <div className="glass rounded-3xl p-5">
    <div className="flex flex-wrap gap-2">
     <button type="button" disabled={submitting} onClick={()=>setBookSource("existing")} className={`rounded-xl px-4 py-2 text-sm font-semibold ${bookSource==="existing"?"bg-black text-white":"bg-neutral-100 text-black"}`}>Mavjud kitobni tanlash</button>
     <button type="button" disabled={submitting} onClick={()=>setBookSource("new")} className={`rounded-xl px-4 py-2 text-sm font-semibold ${bookSource==="new"?"bg-black text-white":"bg-neutral-100 text-black"}`}>Yangi kitob</button>
    </div>
    {bookSource==="existing"?ownBookOptions:<div className="mt-4">
     <Field l="Kitob nomi" ph="Masalan: O'tkan kunlar" name="title" value={values.title} onChange={update} required/>
     <Field l="Muallif" ph="Abdulla Qodiriy" name="author" value={values.author} onChange={update} required/>
     <label className="mb-4 block"><span className="text-xs text-neutral-600">Janr</span><select name="genre" value={values.genre} onChange={update} className="mt-1 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-black">{GENRES.map(genre=><option key={genre} value={genre}>{genre}</option>)}</select></label>
     <label className="mb-4 block"><span className="text-xs text-neutral-600">Tavsif</span><textarea name="description" rows={3} value={values.description} onChange={update} className="mt-1 w-full rounded-xl border border-black/10 bg-white px-4 py-3 text-black"/></label>
     <Drop l="Kitob muqovasi (ixtiyoriy)" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" onChange={event=>setCover(event.target.files?.[0]||null)}/>
     {coverPreview&&<img src={coverPreview} alt="Tanlangan kitob muqovasi" className="mt-3 h-40 w-32 rounded-xl object-cover"/>}
    </div>}
    {mode==="reel"&&<label className="mt-5 flex items-center gap-3 text-sm font-semibold">
     <input type="checkbox" checked={audioEnabled} disabled={submitting} onChange={event=>setAudioEnabled(event.target.checked)}/>
     Audio kitob qo'shish (ixtiyoriy)
    </label>}
    {(mode==="book"||audioEnabled)&&<AudioFilesSection files={audioFiles} setFiles={setAudioFiles} access={access} setAccess={setAccess} disabled={submitting} onError={setError}/>}
   </div>
   {error&&<p role="alert" className="text-sm text-rose-700">{error}</p>}
   {success&&<p role="status" className="text-sm text-emerald-700">{success}</p>}
   {mode==="reel"&&submitting&&<div aria-label="Yuklash jarayoni" className="h-3 overflow-hidden rounded-full bg-neutral-200"><div className="h-full bg-black transition-all" style={{width:`${uploadProgress}%`}}/></div>}
   <div className="flex gap-3">
    <Btn type="submit" disabled={submitting} cn="min-w-0 flex-1 py-3">{submitting?"Yuklanmoqda...":mode==="reel"?"Reel joylash":"Audiokitobni saqlash"}</Btn>
    {submitting&&mode==="reel"&&<Btn type="button" v="g" on={()=>activeUpload.current?.cancel()} cn="px-4 py-3">Bekor qilish</Btn>}
   </div>
  </form>
 </div>;
}
