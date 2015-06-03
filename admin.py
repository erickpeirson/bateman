from django.contrib import admin
from django import forms
from django.core.files import File
import os

from ocr import settings
from .models import DocumentSet, Document
from bateman.tasks import extract_text


def process_documentset(modeladmin, request, queryset):
	for documentset in queryset:
		for document in documentset.documents.all():
			outpath = os.path.join(documentset.output_path(), 
								   '{0}.txt'.format(document.name))
			extract_text.apply_async((document, outpath))
		documentset.attempted = True
		documentset.save()
process_documentset.short_description = "Extract text from selected DocumentSets"


def depth(root):
	"""
	Level of ``root`` below ``MEDIA_ROOT``.
	"""
	basedir = settings.MEDIA_ROOT
	return len(root.split('/')) - len(basedir.split('/')) - int(root.endswith('/'))
	

class DocumentSetForm(forms.ModelForm):
	class Meta:
		model = DocumentSet
		exclude = ['created_by', 'created_on', 'documents', 'processed', 'attempted']	

	def __init__(self, *args, **kwargs):
		super(DocumentSetForm, self).__init__(*args, **kwargs)
		
		choices = [(root, '{pre} {dir}'.format(pre='-'*depth(root),
											   dir=os.path.split(root)[1]))
				   for root, dirs, files in os.walk(settings.MEDIA_ROOT)
				   if depth(root) >= 0]
		help_text = self.fields['directory'].help_text	# Preserve the helptext.
		self.fields['directory'] = forms.ChoiceField(choices=choices, help_text=help_text)
		


class DocumentSetAdmin(admin.ModelAdmin):
	form = DocumentSetForm
	actions = [process_documentset]
	list_display = ['name_and_path', 'created_by', 'created_on', 'size', 'attempted', 'complete']
	readonly_fields =['output_path', 'size']

		
	def save_model(self, request, obj, form, change):
		"""
		"""
		
		# DocumentSet creator.
		if not hasattr(obj, 'created_by'):
			obj.created_by = request.user
		obj.save()

		# Get constituent Documents.
		for dname in os.listdir(obj.directory):
			# Ignore directories and hidden files.
			fullpath = os.path.join(obj.directory, dname)			
			if not os.path.isdir(fullpath) and not dname.startswith('.'):
				doc, created = Document.objects.get_or_create(filepath=fullpath,
															  defaults={'name': dname})
				doc.part_of.add(obj)
				doc.save()


class DocumentAdmin(admin.ModelAdmin):
	list_display = ['name', 'created_on', 'processed', 'size', 'status']
	readonly_fields = ['filepath', 'processed', 'part_of', 'text_content']

admin.site.register(DocumentSet, DocumentSetAdmin)
admin.site.register(Document, DocumentAdmin)