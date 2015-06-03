from __future__ import absolute_import, unicode_literals

from celery import shared_task

from PIL import Image
import magic
import subprocess
from pytesseract import image_to_string
import os
import tempfile

from django.core.files.base import ContentFile
import slate

def is_pdf(document):
	"""
	Use libmagic to decide whether a file is a PDF.
	"""
	return magic.from_file(document.filepath, mime=True) in ['application/pdf', 
															 'application-xpdf']


def textoutput(func):
	"""
	Decorator for functions that extract text from a file.
	"""
	def func_wrapper(document):		
		document.text_content = func(document)
		document.save()
# 		with open(outpath, 'w') as f:
# 			f.write(text)		
		return len(document.text_content)
	return func_wrapper


@shared_task
def convert_pdf(document, density=300, depth=8):
	"""
	Use image-magick to convert the PDF to a TIFF image.
	"""
	
	path, fname = os.path.split(document.filepath)
	temp = tempfile.mkdtemp()
	temppath = "{0}/{1}.tiff".format(temp, fname)
	status = subprocess.call(["convert", "-density", str(density), 
							  document.filepath, 
							  "-depth", str(depth), temppath])

	if status == 0:	# Success!
		return temppath
	raise RuntimeError("convert failed with exit status {status}".format(status=status))


@shared_task
@textoutput	
def slate_extract(document):
	"""
	Use ``slate`` to extract embedded text from a PDF.
	"""

	with open(document.filepath) as f:
		text = '\n\n'.join(slate.PDF(f))
	return text
	
	
@shared_task
@textoutput
def tesseract_extract(document):
	"""
	Use ``tesseract-ocr`` to extract text from ``path``.
	"""

	if is_pdf(document):	
		fpath = convert_pdf(document)	# Convert to an image file.
	else:
		fpath = document.filepath
	return image_to_string(Image.open(fpath))


@shared_task
def extract_text(document, outpath):
	if not document.processed:
		if (slate_extract(document)) <= 0:	# First look for embedded text.
			if (tesseract_extract(document)) <= 0:	# Then perform OCR.
				return
		document.processed = True
		document.save()
	
	# Write contents to `outpath` regardless of whether text was extracted in this
	#  procedure, or was extracted previously.
	with open(outpath, 'w') as f:
		f.write(document.text_content)
			
	return	
