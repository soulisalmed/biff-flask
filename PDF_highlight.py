#!/usr/bin/env python3
from fitz import open as fitzopen
from fitz import Rect , Matrix
from cv2 import dilate , erode,  findContours,  imdecode,  boundingRect,  RETR_CCOMP,  CHAIN_APPROX_SIMPLE
from numpy import ones,  empty,  lexsort,  frombuffer, uint8
from operator import itemgetter
from itertools import groupby
from re import sub
from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, ParagraphProperties
from odf.text import P
from odf.draw import Frame, Image
import os

def Page_Get_Rects(doc,doc_text,name,page):
    cont=b""
    page=doc[page]
    for xref in page._getContents():
        try:
            cont=doc.xrefStream(xref)
        except:
            continue

        if b"1 0.952941 0.658824 RG" in cont:
            cont=cont.replace(b"1 0.952941 0.658824 RG",b"0 0 0 RG")
            cont=cont.replace(b"gs",b" ")
            #cont=re.sub(b"1 0 0 1 (.*) (.*) cm",b"1 0 0 1 0 0 cm",cont)
            cont=sub(b"q\n(.*) 0 0 (.*) (.*) (.*) cm",b"1 0 0 1 0 0 cm",cont)
            doc.updateStream(xref,cont)
            doc_text._deleteObject(xref)
        else:
            doc._deleteObject(xref)

    pix=page.getPixmap()
    pix=pix.getPNGData()
    nparr = frombuffer(pix, uint8)
    img = 255-imdecode(nparr,0)
    kernel = ones((3,3), uint8)
    img=dilate(img,kernel,iterations = 5)
    img=erode(img,kernel,iterations = 5)
    contour,hierarchy = findContours(img,RETR_CCOMP,CHAIN_APPROX_SIMPLE)
    #print(hierarchy)
    nb_contour=len(contour)
    rects=empty((nb_contour,4))
    rects_sorted=empty((nb_contour,4))
    hierarchy_sorted=empty((nb_contour,4))
    
    for i in range(nb_contour):
        #img2=np.ones_like(img)*255.
        rects[i] = boundingRect(contour[i])
    #print(rects)
    rects[:,2]=rects[:,0]+rects[:,2]
    rects[:,3]=rects[:,1]+rects[:,3]
    ind_sorted=lexsort((rects[:,0],rects[:,1]))

    for i in range(nb_contour):
        rects_sorted[i]=rects[ind_sorted[i]]
        hierarchy_sorted[i]=hierarchy[0,ind_sorted[i],:]

    #img2=np.ones_like(img)*255.
    #for i in range(nb_contour):
        #pt1=(int(rects_sorted[i,0]),int(rects_sorted[i,1]))
        #pt2=(int(rects_sorted[i,2]),int(rects_sorted[i,3]))

        #img2 = cv2.rectangle(img2,pt1,pt2,(0,255,0),2)

        #plt.imshow(img2)
        #plt.show()
    return rects_sorted,hierarchy_sorted

def Page_Rect_get_Text(doc,name,page_num,rects,output):
    page=doc[page_num]
    words = page.getText("words")
    output.write("_"*30+"\n")
    output.write(f"page {page_num+1}\n")
    for i in range(rects.shape[0]):
        output.write("\n")
        rect=Rect(rects[i,0],rects[i,1],rects[i,2],rects[i,3])
        mywords = [w for w in words if Rect(w[:4]) in rect]
        mywords.sort(key=itemgetter(3, 0))  # sort by y1, x0 of the word rect
        group = groupby(mywords, key=itemgetter(3))
        for y1, gwords in group:
            output.write(" ".join(w[4] for w in gwords).replace("\n",""))
            output.write("\n")


def Page_Rect_get_Text_odf(doc,name,page_num,rects,hierarchy,output,style_p):
    page=doc[page_num]
    words = page.getText("words")
    output.text.addElement(P(stylename=style_p,text="_"*30))
    output.text.addElement(P(stylename=style_p,text=f"page {page_num+1}"))
    for i in range(rects.shape[0]):
        if hierarchy[i,3]==-1:
            output.text.addElement(P(stylename=style_p,text=""))
            rect=Rect(rects[i,0],rects[i,1],rects[i,2],rects[i,3])
            mywords = [w for w in words if Rect(w[:4]) in rect]
            mywords.sort(key=itemgetter(3, 0))  # sort by y1, x0 of the word rect
            group = groupby(mywords, key=itemgetter(3))
            out_text=P(stylename=style_p,text="")
            for y1, gwords in group:
                out_text.addText(" ".join(w[4] for w in gwords).replace("\n"," "))
                out_text.addText(" ")
            output.text.addElement(out_text)
        if hierarchy[i,3]!=-1:
            output.text.addElement(P(stylename=style_p,text=""))
            out_img=P()
            #ncc=int(hierarchy[i,3])
            ncc=i
            clip = Rect(rects[ncc,0],rects[ncc,1],rects[ncc,2],rects[ncc,3])
            pix = page.getPixmap(matrix=Matrix(2,2),clip=clip)
            name_image=f"Pictures/image-{page.number}-{i}.png"
            #liste_tampon.append(name_tampon)
            #pix.writePNG(name_image)
            pix_png=pix.getPNGData()
            h=pix.height/pix.xres
            w=pix.width/pix.yres
            frame=Frame(width=f"{w}in",height=f"{h}in",anchortype="paragraph")
            href=output.addPicture(name_image,mediatype="png",content=pix_png)#
            frame.addElement(Image(href=f"./{href}"))
            out_img.addElement(frame)
            output.text.addElement(out_img)
    return output
            
def extract_highlight(name):
    open(f"{name}.txt", 'w').close()
    output=open(f"{name}.txt","a")
    doc_mask=fitzopen(name)
    doc_text=fitzopen(name)
    nb_pages=doc_text.pageCount
    for i in range(nb_pages):
        rect,hierarchy=Page_Get_Rects(doc_mask,name,i)
        if rect.shape[0]>0:
            Page_Rect_get_Text(doc_text,name,i,rect,output)
    output.close()

def extract_highlight_odf(name):
    textdoc = OpenDocumentText()
    location=os.path.join("/tmp/pdf_highlight/",name)
    doc_mask=fitzopen(location)
    doc_text=fitzopen(location)
    nb_pages=doc_text.pageCount
    style_p=Style(name="P1",family="paragraph",parentstylename="Standard")
    p_prop = ParagraphProperties(textalign="justify",justifysingleword="false")
    style_p.addElement(p_prop)
    textdoc.automaticstyles.addElement(style_p)
    textdoc.text.addElement(P(stylename=style_p,text=f"{name}\n\n"))

    for i in range(nb_pages):
        rect,hierarchy=Page_Get_Rects(doc_mask,doc_text,name,i)
        if rect.shape[0]>0:
            textdoc=Page_Rect_get_Text_odf(doc_text,name,i,rect,hierarchy,textdoc,style_p)
    
    text_name=name.replace(".pdf",".odt")
    location_out=os.path.join("/tmp/pdf_highlight/",text_name)

    textdoc.save(location_out)
    #print('fin')
    return text_name,location_out
