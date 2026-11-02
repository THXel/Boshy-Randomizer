using System;
using System.IO;
using System.Linq;
using UndertaleModLib.Util;
using UndertaleModLib.Decompiler;
string root = Environment.GetEnvironmentVariable("BOSHY_UNDERTALE_EXPORT") ?? throw new Exception("Missing export directory");
Directory.CreateDirectory(root);
using (TextureWorker worker = new()) {
 foreach (var spr in Data.Sprites.Where(x => new[]{"spr_heart", "spr_heartbreak", "spr_heartshards", "spr_gameoverbg"}.Contains(x.Name.Content))) {
  for (int i=0; i<spr.Textures.Count; i++) worker.ExportAsPNG(spr.Textures[i].Texture, Path.Combine(root, spr.Name.Content+"_"+i+".png"), null, true);
 }
}
foreach (var snd in Data.Sounds.Where(x=>new[]{"snd_break1", "snd_break2"}.Contains(x.Name.Content))) File.WriteAllBytes(Path.Combine(root,snd.Name.Content+".wav"),snd.AudioFile.Data);

// Export the local game's bitmap font; no replacement font download is needed.
foreach (string name in new[]{"fnt_main", "fnt_ja_main"}) {
 var font = Data.Fonts.First(x => x.Name.Content == name);
 using (TextureWorker worker = new()) worker.ExportAsPNG(font.Texture, Path.Combine(root, name+".png"), null, true);
 var glyphs = font.Glyphs.Select(g => new { code=(int)g.Character, x=(int)g.SourceX, y=(int)g.SourceY, width=(int)g.SourceWidth, height=(int)g.SourceHeight, shift=(int)g.Shift, offset=(int)g.Offset }).ToArray();
 File.WriteAllText(Path.Combine(root,name+".json"), System.Text.Json.JsonSerializer.Serialize(new { name=name, line_height=36, glyphs=glyphs }));
}
