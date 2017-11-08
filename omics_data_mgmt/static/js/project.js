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


// Disable nav project search until 3+ characters have been input
// (not counting keyword)
$(document).ready(function() {
     $('#omics-nav-search-submit').attr('disabled', 'disabled');
     $('#omics-nav-search-input').keyup(function() {
        v = $(this).val();

        if((v.indexOf(':') !== -1 && v.split(':')[1].length > 2) ||
            (v.indexOf(':') === -1 && v.length > 2)) {
           $('#omics-nav-search-submit').attr('disabled', false);
        }

        else if((v.indexOf(':') !== -1 && v.split(':')[1].length <= 2) ||
            (v.indexOf(':') === -1 && v.length <= 2)) {
           $('#omics-nav-search-submit').attr('disabled', true);
        }
     });
 });
