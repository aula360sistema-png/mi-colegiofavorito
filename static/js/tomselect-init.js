/* TomSelect init for searchable selects */
document.addEventListener('DOMContentLoaded', function () {
  if (typeof TomSelect === 'undefined') return;
  document.querySelectorAll('select.searchable').forEach(function (el) {
    new TomSelect(el, {
      maxOptions: null,
      render: {
        option: function (data, escape) {
          var sub = data.extra_sub ? '<div class="text-xs text-gray-500">' + escape(data.extra_sub) + '</div>' : '';
          var desc = data.extra_desc ? '<div class="text-xs text-gray-400 italic">' + escape(data.extra_desc) + '</div>' : '';
          return '<div class="py-1 px-2">' +
            '<div class="font-medium">' + escape(data.text) + '</div>' +
            sub + desc + '</div>';
        },
        item: function (data, escape) {
          var sub = data.extra_sub ? ' <span class="text-xs text-gray-500">(' + escape(data.extra_sub) + ')</span>' : '';
          return '<div>' + escape(data.text) + sub + '</div>';
        }
      }
    });
  });
});
