var state = {
  username: '',
  profile: null,
  tasks: [],
  trends: [],
  guideCache: {}
};

var API_BASE = 'http://127.0.0.1:5000';

function $(id) { return document.getElementById(id); }
function show(id) {
  document.querySelectorAll('.screen').forEach(function (s) { s.classList.remove('active'); });
  $(id).classList.add('active');
}
