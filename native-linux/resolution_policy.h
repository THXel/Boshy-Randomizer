/* Windowed 4:3 presets; reserve the original engine's 35 px title bar.
 * Stretched fullscreen stays the game's final, unmodified action. */
static unsigned resolution_limit(int width,int height){
 int value=(height-35)*4/3;if(value>width)value=width;if(value>2880)value=2880;
 value=value/4*4;return value<320?320:(unsigned)value;
}
static unsigned resolution_next(unsigned current,unsigned limit,int direction){
 static const unsigned sizes[]={320,480,640,800,880,960,1024,1152,1280,1440,1600,1760,1920,2048,2560,2880};
 unsigned result=direction>0?limit:320;
 for(unsigned i=0;i<sizeof(sizes)/sizeof(*sizes);i++){
  unsigned n=sizes[i];if(n>limit)continue;
  if(direction>0&&n>current&&n<result)result=n;
  if(direction<0&&n<current&&n>result)result=n;
 }
 if(direction<0&&limit<current&&limit>result)result=limit;
 return result;
}
