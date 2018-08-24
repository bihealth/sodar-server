// Set up DataTables for search tables
$(document).ready(function() {
    /*****************
     Set up DataTables
     *****************/

    $.fn.dataTable.ext.classes.sPageButton =
        'btn btn-secondary omics-list-btn ml-1 omics-paginate-button';

    $('.omics-search-table').each(function() {
        $(this).DataTable({
            scrollX: false,
            paging: true,
            pageLength: window.searchPagination,
            scrollCollapse: true,
            info: false,
            language: {
                paginate: {
                    previous: '<i class="fa fa-arrow-circle-left"></i> Previous',
                    next: '<i class="fa fa-arrow-circle-right"></i> Next'
                }
            },
            dom: 'tp',
            fnDrawCallback: function() {
                // Highlight pagination
                var currentPage = $(this).DataTable().page.info().page;

                $(this).closest('.card-body').find('.omics-paginate-button').each(function() {
                    var btnPage = $(this).attr('data-dt-idx');

                    if (btnPage == currentPage + 1) {
                        $(this).removeClass('btn-secondary').addClass('btn-success');
                    }
                });

                // Update overflow status
                modifyCellOverflow();
            }
        });

        // Hide pagination if only one page
        if ($(this).DataTable().page.info().pages === 1) {
            $(this).next('.dataTables_paginate').hide();
        }

        // Display card once table has been initialized
        $(this).closest('div.omics-search-card').show();
    });

    // Display not found once all DataTables have been initialized
    $('div#omics-search-not-found-alert').removeClass('d-none');

    // Update overflow status
    //modifyCellOverflow();

    /*********
     Filtering
     *********/

    $('.omics-search-filter').keyup(function () {
        var dt = $(this).closest('.omics-search-card').find('table').dataTable();
        var v = $(this).val();
        dt.fnFilter(v);
    });

    /********************
     Pagination Highlight
     ********************/
});
