#ifndef BOSHY_RUNTIME_ROOT_H
#define BOSHY_RUNTIME_ROOT_H
static int runtime_root(char *exe,char *directory){
 const char *root=getenv("BOSHY_RUNTIME_ROOT"),*prefix=getenv("WINEPREFIX");char wanted[4096],cwd[MAX_PATH];
 if(!root||!prefix||root[0]!='/'||strlen(root)>180)return 0;
 snprintf(wanted,sizeof(wanted),"%s/wineprefix",root);if(strcmp(prefix,wanted))return 0;
 if(!GetCurrentDirectoryA(MAX_PATH,cwd))return 0;
 snprintf(wanted,sizeof(wanted),"Z:%s",root);for(char*p=wanted;*p;p++)if(*p=='/')*p='\\';
 if(lstrcmpiA(cwd,wanted))return 0;
 snprintf(directory,MAX_PATH,"%s\\IWBTB",cwd);
 snprintf(exe,MAX_PATH,"%s\\I Wanna Be The Boshy.exe",directory);return 1;
}
#endif
