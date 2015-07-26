from django.views.generic import CreateView, DetailView

from candidates.cache import get_post_cached
from candidates.popit import create_popit_api_object
from auth_helpers.views import GroupRequiredMixin
from elections.mixins import ElectionMixin

from .forms import UploadDocumentForm
from .models import DOCUMENT_UPLOADERS_GROUP_NAME, OfficialDocument


class DocumentView(DetailView):
    model = OfficialDocument

    def get_context_data(self, **kwargs):
        context = super(DocumentView, self).get_context_data(**kwargs)
        api = create_popit_api_object()
        post_data = get_post_cached(api, self.object.post_id)['result']
        context['post_label'] = post_data['label']
        return context

class CreateDocumentView(ElectionMixin, GroupRequiredMixin, CreateView):
    required_group_name = DOCUMENT_UPLOADERS_GROUP_NAME

    form_class = UploadDocumentForm
    template_name = "official_documents/upload_document_form.html"

    def get_initial(self):
        return {
            'election': self.election,
            'document_type': OfficialDocument.NOMINATION_PAPER,
            'post_id': self.kwargs['post_id'],
        }

    def get_context_data(self, **kwargs):
        context = super(CreateDocumentView, self).get_context_data(**kwargs)
        api = create_popit_api_object()
        post_data = get_post_cached(api, self.kwargs['post_id'])['result']
        context['post_label'] = post_data['label']
        return context
