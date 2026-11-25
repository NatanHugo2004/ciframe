angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory) {
  var COR_ACORDE = '#2E1C74';

  var paraSequencia = function(item) {
    return {
      'index': item.id,
      'acordes': item.acordes.map(function(acorde) {
        return { 'acorde': acorde, 'cor': COR_ACORDE };
      })
    };
  };

  var vm = this;
  vm.sequenciasFamosas = [];
  vm.acordesDisponiveis = [];
  vm.acordeSelecionado = '';
  vm.novaSequencia = [];
  vm.erroCadastro = '';
  vm.carregandoCatalogo = true;
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech = "";
  vm.musics = [];
  vm.generos = [];
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  var carregarCatalogo = function() {
    $http.get('/sequencias')
      .success(function(data) {
        vm.sequenciasFamosas = data.map(paraSequencia);
        vm.carregandoCatalogo = false;
      })
      .error(function() {
        vm.erroCadastro = 'Não foi possível carregar o catálogo.';
        vm.carregandoCatalogo = false;
      });
  };

  $http.get('/acordes').success(function(data) {
    vm.acordesDisponiveis = data;
  });
  $http.get('/generos').success(function(data) {
    vm.generos = data;
  });
  carregarCatalogo();

  vm.adicionarAcorde = function() {
    var acorde = vm.acordeSelecionado;
    if (!acorde) {
      return;
    }
    vm.novaSequencia.push({ 'acorde': acorde, 'cor': COR_ACORDE });
    vm.acordeSelecionado = '';
  };

  vm.removerUltimoAcorde = function() {
    vm.novaSequencia.pop();
  };

  vm.cadastrarSequencia = function() {
    var acordes = vm.novaSequencia.map(function(item) {
      return item.acorde;
    });
    if (acordes.length === 0) {
      vm.erroCadastro = 'Escolha ao menos um acorde.';
      return;
    }
    $http.post('/sequencias', { 'acordes': acordes })
      .success(function() {
        vm.novaSequencia = [];
        vm.erroCadastro = '';
        carregarCatalogo();
      })
      .error(function(data) {
        vm.erroCadastro = (data && data.erro) || 'Ops! Algo errado.';
      });
  };

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  var createChordsString = function(chords) {
    var str = "";
    for (var i = 0; i < chords.length; i++) {
      str = str.concat(chords[i].acorde, ',');
    }
    return str.substring(0, str.length-1);
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var apiUrl = "";
    var searchString = "similares?sequencia=".concat(createChordsString(vm.minhaSequencia.acordes));
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }
    $http.get(apiUrl.concat(searchString))
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };
});
