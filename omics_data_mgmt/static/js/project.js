/* Project specific Javascript goes here. */

/*
Formatting hack to get around crispy-forms unfortunate hardcoding
in helpers.FormHelper:

    if template_pack == 'bootstrap4':
        grid_colum_matcher = re.compile('\w*col-(xs|sm|md|lg|xl)-\d+\w*')
        using_grid_layout = (grid_colum_matcher.match(self.label_class) or
                             grid_colum_matcher.match(self.field_class))
        if using_grid_layout:
            items['using_grid_layout'] = True

Issues with the above approach:

1. Fragile: Assumes Bootstrap 4's API doesn't change (it does)
2. Unforgiving: Doesn't allow for any variation in template design
3. Really Unforgiving: No way to override this behavior
4. Undocumented: No mention in the documentation, or it's too hard for me to find
*/
$('.form-group').removeClass('row');


// From: https://stackoverflow.com/a/14919494
function humanFileSize(bytes, si) {
    var thresh = si ? 1000 : 1024;
    if(Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = si
        ? ['kB','MB','GB','TB','PB','EB','ZB','YB']
        : ['KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(Math.abs(bytes) >= thresh && u < units.length - 1);
    return bytes.toFixed(1)+' '+units[u];
}


// Initialize Shepherd Tour
var tourEnabled = false;  // Needs to set true if there is content
    tour = new Shepherd.Tour({
        defaults: {
            classes: 'shepherd-theme-default'
        }
    });


// Set up Bootstrap popover
$('[data-toggle="popover"]').popover({
    container: 'body'
});


// Set up Bootstrap tooltip
$(function(){
    $('[data-toggle="tooltip"]').tooltip({
        trigger : 'hover'
    });
});


// Disable nav project search until 3+ characters have been input
// (not counting keyword)
$(document).ready(function() {
     $('#omics-nav-search-submit').attr('disabled', 'disabled');
     $('#omics-nav-search-input').keyup(function() {
        v = $(this).val();

        if(v.length > 2) {
           $('#omics-nav-search-submit').attr('disabled', false);
        }

        else {
           $('#omics-nav-search-submit').attr('disabled', true);
        }
     });
 });


// Home page project list filtering
$(document).ready(function() {
    $('.omics-pr-home-display-filtered').hide();
    $('.omics-pr-home-display-notfound').hide();
    $('.omics-pr-home-display-nostars').hide();

    // Filter input
    $('#omics-pr-project-list-filter').keyup(function () {
        v = $(this).val().toLowerCase();
        var valFound = false;
        $('.omics-pr-home-display-nostars').hide();

        if (v.length > 2) {
            $('.omics-pr-home-display-default').hide();
            $('#omics-pr-project-list-filter').removeClass('text-danger').addClass('text-success');
            $('#omics-pr-project-list-link-star').html('<i class="fa fa-star-o"></i> Starred');

            $('.omics-pr-home-display-filtered').each(function () {
                var titleTxt = $(this).find('td:nth-child(1)').attr('orig-txt');
                var descTxt = $(this).find('td:nth-child(2)').attr('orig-txt');

                if ($(this).find('td:nth-child(1) a').text().toLowerCase().indexOf(v) !== -1 ||
                    $(this).find('td:nth-child(2)').text().toLowerCase().indexOf(v) !== -1) {
                    // Reset content for updating the highlight
                    $(this).find('td:nth-child(1) a').html(titleTxt);
                    $(this).find('td:nth-child(2)').html(descTxt);

                    // Highlight
                    var pattern = new RegExp("(" + v + ")", "gi");
                    var titlePos = titleTxt.toLowerCase().indexOf(v);
                    var descPos = descTxt.toLowerCase().indexOf(v);

                    if (titlePos !== -1) {
                        var titleVal = titleTxt.substring(titlePos, titlePos + v.length);
                        $(this).find('td:nth-child(1) a').html(titleTxt.replace(pattern, '<span class="omics-search-highlight">' + titleVal + '</span>'));
                    }

                    if (descPos !== -1) {
                        var descVal = descTxt.substring(descPos, descPos + v.length);
                        $(this).find('td:nth-child(2)').html(descTxt.replace(pattern, '<span class="omics-search-highlight">' + descVal + '</span>'));
                    }

                    $(this).show();
                    valFound = true;
                    $('.omics-pr-home-display-notfound').hide();
                }

                else {
                    $(this).hide();
                }
            });

            if (valFound === false) {
                $('.omics-pr-home-display-notfound').show();
            }
        }

        else {
            $('.omics-pr-home-display-default').show();
            $('.omics-pr-home-display-filtered').hide();
            $('.omics-pr-home-display-notfound').hide();
            $('#omics-pr-project-list-filter').addClass('text-danger').removeClass('text-success');
        }
    });

    // Filter by starred
    $('#omics-pr-project-list-link-star').click(function () {
        $('.omics-pr-home-display-notfound').hide();

        // Reset search terms
        $('.omics-pr-home-display-filtered').each(function () {
            // Reset filter highlights and value
            var titleTxt = $(this).find('td:nth-child(1)').attr('orig-txt');
            var descTxt = $(this).find('td:nth-child(2)').attr('orig-txt');
            $(this).find('td:nth-child(1) a').html(titleTxt);
            $(this).find('td:nth-child(2)').html(descTxt);
            $(this).hide();
            $('#omics-pr-project-list-filter').val('');
        });

        if ($(this).attr('filter-mode') === '0') {
            $('.omics-pr-home-display-default').hide();
            $('.omics-pr-home-display-starred').show();
            $('#omics-pr-project-list-link-star').html('<i class="fa fa-star"></i> Starred');
            $(this).attr('filter-mode', '1');

            if ($('.omics-pr-home-display-starred').length === 0) {
                $('.omics-pr-home-display-nostars').show();
            }
        }

        else if ($(this).attr('filter-mode') === '1') {
            $('.omics-pr-home-display-nostars').hide();
            $('.omics-pr-home-display-default').show();
            $('#omics-pr-project-list-link-star').html('<i class="fa fa-star-o"></i> Starred');
            $(this).attr('filter-mode', '0');
        }
    });
});

// Star/unstar project with AJAX
$(document).ready(function() {
    $('#omics-pr-link-project-star').click(function () {
        $.post({
            url: $(this).attr('star-url'),
            method: 'POST',
            dataType: 'json',
            headers: {
                'X-CSRFToken': $(this).attr('csrf-token')
            }
        }).done(function (data) {
            console.log('Star clicked: ' + data);  // DEBUG
            if (data === 1) {
                 $('#omics-pr-btn-star-icon').removeClass(
                     'text-muted').addClass('text-warning').removeClass(
                         'fa-star-o').addClass('fa-star');
                 $('#omics-pr-link-project-star').attr('data-original-title', 'Unstar');
            }
            else {
                $('#omics-pr-btn-star-icon').removeClass(
                     'text-warning').addClass('text-muted').removeClass(
                         'fa-star').addClass('fa-star-o');
                $('#omics-pr-link-project-star').attr('data-original-title', 'Star');
            }
        }).fail(function() {
            alert('Error: unable to set project star!');
        });
    });
});
