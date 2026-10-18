/* MMF 0x435960 / 0x449640: OI list at Frame+0x480, 122-byte records.
 * Unlike the original unbounded search, refuse missing identities. */
static int runtime_oi_index(U oi){
 U frame=*(U*)0x459a98;if(frame<65536||oi>=32768)return -1;
 U list=*(U*)(frame+0x480),count=*(unsigned short*)(frame+0x8f2);
 if(list<65536||!count||count>2048)return -1;
 for(U i=0;i<count;i++)if(*(unsigned short*)(list+i*122)==oi)return (int)i;
 return -1;
}
