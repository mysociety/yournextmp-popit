from __future__ import unicode_literals

form_simple_fields = {
    'honorific_prefix': '',
    'name': '',
    'honorific_suffix': '',
    'email': '',
    'birth_date': '',
    'gender': '',
}

form_complex_fields_locations = {
    'wikipedia_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'wikipedia',
    },
    'linkedin_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'linkedin',
    },
    'homepage_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'homepage',
    },
    'twitter_username': {
        'sub_array': 'contact_details',
        'info_type_key': 'contact_type',
        'info_value_key': 'value',
        'info_type': 'twitter',
    },
    'facebook_personal_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'facebook personal',
    },
    'facebook_page_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'facebook page',
    },
    'party_ppc_page_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'party candidate page',
        'old_info_type': 'party PPC page',
    }
}

CSV_ROW_FIELDS = [
    'id',
    'name',
    'honorific_prefix',
    'honorific_suffix',
    'gender',
    'birth_date',
    'election',
    'party_id',
    'party_name',
    'post_id',
    'post_label',
    'mapit_url',
    'elected',
    'email',
    'twitter_username',
    'facebook_page_url',
    'party_ppc_page_url',
    'facebook_personal_url',
    'homepage_url',
    'wikipedia_url',
    'linkedin_url',
    'image_url',
    'proxy_image_url_template',
    'image_copyright',
    'image_uploading_user',
    'image_uploading_user_notes',
]
