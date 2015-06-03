import os

from django.db import models
from django.contrib.auth.models import User

from ocr import settings

class Path(models.Model):
	path = models.TextField()

class Document(models.Model):
	"""
	Represents a document at a specific location.
	
	There may be no more than one :class:`.Document` per unique location.
	"""
	
	filepath = models.CharField(max_length=255, unique=True)
	"""Location of original document file."""
	
	text_content = models.TextField()
	"""Plain text extracted from the `Document`."""
	
	processed = models.BooleanField(default=False)
	"""Indicates whether text extraction has been performed."""

	part_of = models.ManyToManyField('DocumentSet', related_name='documents')
	
	created_on = models.DateTimeField(auto_now_add=True)	
	
	@property
	def name(self):
		base, head = os.path.split(self.filepath)
		return head
	
	def status(self):
		"""
		Indicates whether there is a problem extracting text from this Document.
		"""
		if self.processed and self.size() <= 0:
			return False
		else:
			return True
	status.boolean = True
	
	def size(self):
		return len(self.text_content)
	

class DocumentSet(models.Model):
	"""
	Represents a collection of documents in a particular directory.
	
	There may be more than one :class:`.DocumentSet` for a particular directory, and their
	constituent :class:`.Document` may overlap.
	"""
	
	class Meta:
		verbose_name = 'DocumentSet'
		verbose_name_plural = 'DocumentSets'
	
	name = models.SlugField(max_length=255, unique=True, help_text="""The unique name for
		this DocumentSet. It may contain only lowercase alphanumeric characters, hyphens, 
		and underscores. This name will be used to generate an output directory for
		extracted text files.""")
	"""Unique name for a collection of documents."""

	directory = models.CharField(max_length=255, help_text="""A directory containing
		documents from which text is to be extracted. Note that subdirectories will be
		ignored.""")
	"""Location of the directory containing the documents."""
	
	created_by = models.ForeignKey(User)
	"""User who created the `DocumentSet`."""
	
	created_on = models.DateTimeField(auto_now_add=True)
	"""DateTime when the `DocumentSet` was created."""
	
	attempted = models.BooleanField(default=False)
	"""Indicates whether text extraction has been attempted."""

	def output_path(self):
		return os.path.join(settings.OUTPUT_ROOT, self.name)
	output_path.help_text = """Location where text output will be stored. If creating a
		new DocumentSet, a new subdirectory will be created at this location."""

	@property
	def name_and_path(self):
		return self.__unicode__()
		
	@property
	def size(self):
		return self.documents.count()

	def complete(self):
		return sum([d.processed for d in self.documents.all()]) == self.documents.count()
	complete.boolean = True
		
	def save(self, *args, **kwargs):
		if not os.path.exists(self.output_path()):
			os.makedirs(self.output_path())
		super(DocumentSet, self).save(*args, **kwargs)		
		
	def __unicode__(self):
		return unicode('{name} ({dir})'.format(name=self.name, dir=self.directory))