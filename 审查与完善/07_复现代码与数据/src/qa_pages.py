from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]/'paper'/'rendered-final2'
paths=sorted(root.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[1]))
for batch in range((len(paths)+8)//9):
    canvas=Image.new('RGB',(1080,1440),'#ddd')
    for k,p in enumerate(paths[batch*9:(batch+1)*9]):
        im=Image.open(p).convert('RGB');im.thumbnail((350,430));tile=Image.new('RGB',(360,480),'white');tile.paste(im,((360-im.width)//2,25));ImageDraw.Draw(tile).text((8,5),f'Page {batch*9+k+1}',fill='black');canvas.paste(tile,((k%3)*360,(k//3)*480))
    canvas.save(root/f'contact-{batch+1}.jpg',quality=92)
print(len(paths))
