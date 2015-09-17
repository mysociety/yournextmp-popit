/* Get the element that should have its visibility changed to hide or show
   a Select2. */

function getSelect2Enclosure(selectElement) {
  /* This assumes that there's a label that's a sibling of the
   * Select2, and that they're the only elements in a containing
   * element (the one that will be returned by this function) */
  return selectElement.select2('container').parent();
}

/* Change the visibility of a Select2 widget; select2Element should be a
   jQuery-wrapped element */

function setSelect2Visibility(select2Element, visibility) {
  /* If visibility is false, this both disables the Select2 boxes and
   * hides them by hiding their enclosing element. Otherwise it
   * enables it and makes the enclosure visible. */
  var enclosure = getSelect2Enclosure(select2Element);
  select2Element.prop(
    'disabled',
    !visibility
  );
  if (visibility) {
    enclosure.show()
  } else {
    enclosure.hide();
  }
}

/* Make all the party drop-downs into Select2 widgets */

function setUpPartySelect2s() {
  $('.party-select').select2({width: '100%'});
}

/* Make all the post drop-downs into Select2 widgets */

function setUpPostSelect2s() {
  $('.post-select').each(function(i) {
    var postSelect = $(this),
      hidden = postSelect.prop('tagName') == 'INPUT' &&
         postSelect.attr('type') == 'hidden';
    /* If it's a real select box (not a hidden input) make it into a
     * Select2 box */
    if (!hidden) {
      postSelect.select2({
        placeholder: 'Post',
        allowClear: true,
        width: '100%'
      });
    }
    postSelect.on('change', function (e) {
      updateFields();
    });
    updateFields();
  });
}

/* Update the visibility of the party and post drop-downs for a particular
   election */

function updateSelectsForElection(show, election) {
  /* Whether we should show the party and post selects is
     determined by the boolean 'show'. */
  var partySelectToShowID,
      partyPositionToShowID,
      postID = $('#id_constituency_' + election).val(),
      partySet;
  if (postID) {
    partySet = postIDToPartySet[postID];
  }
  if (show) {
    if (postID) {
      partySelectToShowID = 'id_party_' + partySet + '_' + election;
      partyPositionToShowID = 'id_party_list_position_' + partySet + '_' + election;
      $('.party-select-' + election).each(function(i) {
        setSelect2Visibility(
          $(this),
          $(this).attr('id') == partySelectToShowID
        );
      });
      $('.party-position-' + election).each(function(i) {
        $(this).toggle($(this).attr('id') == partyPositionToShowID);
      });
    } else {
      /* Then just show the first party select and hide the others: */
      $('.party-select-' + election).each(function(i) {
        setSelect2Visibility($(this), i == 0);
      });
      $('.party-position-' + election).each(function(i) {
        $(this).toggle(i == 0);
      });
    }
  } else {
    $('.party-select-' + election).each(function(i) {
      setSelect2Visibility($(this), false);
    });
    $('.party-position-' + election).hide();

  }
  setSelect2Visibility($('#id_constituency_' + election), show);
}

/* Make sure that the party and constituency select boxes are updated
   when you choose whether the candidate is standing in that election
   or not. */

function setUpStandingCheckbox() {
  $('#person-details select.standing-select').on('change', function() {
    updateFields();
  });
}

/* This should be called whenever the select drop-downs for party
   and post that have to be shown might have to be shown.  */

function updateFields() {
  $('#person-details select.standing-select').each(function(i) {
    var standing = $(this).val() == 'standing',
        match = /^id_standing_(.*)/.exec($(this).attr('id')),
        election = match[1];
    updateSelectsForElection(standing, election); });
}

$(document).ready(function() {
  setUpPartySelect2s();
  setUpPostSelect2s();
  setUpStandingCheckbox();
  updateFields();
});
