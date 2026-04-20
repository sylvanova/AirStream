import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:just_audio/just_audio.dart';
import '../models/station.dart';
import '../services/radio_api.dart';
import '../services/audio_service.dart';
import '../services/storage_service.dart';
import '../widgets/station_tile.dart';

class HomeScreen extends StatefulWidget {
  final AudioPlayerHandler audioHandler;

  const HomeScreen({super.key, required this.audioHandler});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Station> _stations = [];
  List<Map<String, dynamic>> _countries = [];
  List<Map<String, dynamic>> _tags = [];
  Set<String> _favoriteUuids = {};
  Station? _currentStation;
  bool _isLoading = true;
  String? _errorMessage;
  bool _showingFavorites = false;

  String _selectedCountryCode = '';
  String _selectedTag = '';
  final _searchController = TextEditingController();
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _loadInitialData();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadInitialData() async {
    setState(() => _isLoading = true);
    try {
      final results = await Future.wait([
        RadioApi.fetchTopStations(),
        RadioApi.fetchCountries(),
        RadioApi.fetchTags(),
        StorageService.getFavoriteUuids(),
      ]);
      final stations = results[0] as List<Station>;
      if (stations.isNotEmpty) {
        await StorageService.saveCachedStations(stations);
      }
      final countries = results[1] as List<Map<String, dynamic>>;
      final tags = results[2] as List<Map<String, dynamic>>;
      debugPrint('AIRSTREAM: Loaded ${stations.length} stations, ${countries.length} countries, ${tags.length} tags');
      if (countries.isNotEmpty) debugPrint('AIRSTREAM: First country: ${countries[0]}');
      if (tags.isNotEmpty) debugPrint('AIRSTREAM: First tag: ${tags[0]}');
      setState(() {
        _stations = stations.isEmpty ? [] : stations;
        _countries = countries;
        _tags = tags;
        _favoriteUuids = (results[3] as List<String>).toSet();
        _isLoading = false;
      });
      if (stations.isEmpty) {
        await _loadCached();
      } else {
        SemanticsService.announce(
            '${stations.length} stations loaded', TextDirection.ltr);
      }
      unawaited(_rehydratePendingFavorites());
    } catch (e) {
      await _loadCached();
    }
  }

  Future<void> _rehydratePendingFavorites() async {
    final pending = await StorageService.pendingFavoriteUuids();
    if (pending.isEmpty) return;
    try {
      final fresh = await RadioApi.fetchStationsByUuid(pending);
      await StorageService.rehydrateFavorites(fresh);
    } catch (e) {
      debugPrint('AIRSTREAM: favorite rehydrate failed: $e');
    }
  }

  Future<void> _loadCached() async {
    final cached = await StorageService.getCachedStations();
    setState(() {
      _stations = cached;
      _isLoading = false;
      _errorMessage =
          cached.isEmpty ? 'Could not load stations' : 'Offline mode';
    });
    if (cached.isNotEmpty) {
      SemanticsService.announce(
          'Offline. ${cached.length} cached stations', TextDirection.ltr);
    }
  }

  void _onSearchChanged(String text) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () => _doSearch());
  }

  Future<void> _doSearch() async {
    final name = _searchController.text.trim();
    setState(() => _isLoading = true);
    try {
      List<Station> results;
      if (name.isEmpty && _selectedCountryCode.isEmpty && _selectedTag.isEmpty) {
        results = await RadioApi.fetchTopStations();
      } else {
        results = await RadioApi.searchStations(
          name: name,
          countrycode: _selectedCountryCode,
          tag: _selectedTag,
        );
      }
      setState(() {
        _stations = results;
        _isLoading = false;
        _showingFavorites = false;
      });
      SemanticsService.announce(
          results.isEmpty
              ? 'No stations found'
              : 'Found ${results.length} stations',
          TextDirection.ltr);
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _playStation(Station station) async {
    setState(() => _currentStation = station);
    try {
      debugPrint('AIRSTREAM: Playing ${station.name} - ${station.urlResolved}');
      await widget.audioHandler.playStation(station);
      debugPrint('AIRSTREAM: Play started OK');
      SemanticsService.announce(
          'Now playing: ${station.name}', TextDirection.ltr);
    } catch (e) {
      debugPrint('AIRSTREAM: Play error: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  Future<void> _togglePause() async {
    if (widget.audioHandler.isPlaying) {
      await widget.audioHandler.pause();
      SemanticsService.announce('Paused', TextDirection.ltr);
    } else if (widget.audioHandler.isPaused) {
      await widget.audioHandler.play();
      if (_currentStation != null) {
        SemanticsService.announce(
            'Now playing: ${_currentStation!.name}', TextDirection.ltr);
      }
    }
  }

  Future<void> _toggleFavorite(Station station) async {
    final uuid = station.stationuuid;
    debugPrint('AIRSTREAM: toggleFavorite ${station.name}, isFav=${_favoriteUuids.contains(uuid)}');
    if (_favoriteUuids.contains(uuid)) {
      await StorageService.removeFavorite(uuid);
      if (station.isCustom) await StorageService.removeCustomStation(uuid);
      setState(() => _favoriteUuids.remove(uuid));
      SemanticsService.announce(
          '${station.name} removed from favorites', TextDirection.ltr);
    } else {
      await StorageService.addFavorite(station);
      setState(() => _favoriteUuids.add(uuid));
      SemanticsService.announce(
          '${station.name} added to favorites', TextDirection.ltr);
    }
  }

  Future<void> _showFavorites() async {
    final favorites = await StorageService.getFavorites();
    final custom = await StorageService.getCustomStations();
    setState(() {
      _favoriteUuids = favorites.map((s) => s.stationuuid).toSet();
      _showingFavorites = !_showingFavorites;
    });
    if (_showingFavorites) {
      final allFavs = [...favorites, ...custom];
      setState(() => _stations = allFavs);
      SemanticsService.announce(
          'Favorites. ${allFavs.length} stations', TextDirection.ltr);
    } else {
      _doSearch(); // Reload normal list
    }
  }

  void _showAddStationDialog() {
    final nameCtrl = TextEditingController();
    final urlCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Station'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameCtrl,
              decoration: const InputDecoration(
                labelText: 'Station name',
              ),
              autofocus: true,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: urlCtrl,
              decoration: const InputDecoration(
                labelText: 'Stream URL',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              final name = nameCtrl.text.trim();
              final url = urlCtrl.text.trim();
              if (name.isEmpty || url.isEmpty) return;
              await StorageService.addCustomStation(name, url);
              if (ctx.mounted) Navigator.pop(ctx);
              SemanticsService.announce(
                  '$name added', TextDirection.ltr);
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  void _showFilterDialog(String title, List<Map<String, String>> options, String currentValue, void Function(String) onSelected) {
    showDialog(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: Text(title),
        children: options.map((opt) => SimpleDialogOption(
          onPressed: () {
            Navigator.pop(ctx);
            onSelected(opt['value']!);
          },
          child: Text(opt['name']!),
        )).toList(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AirStream'),
        actions: [
          IconButton(
            icon: Icon(
              _showingFavorites ? Icons.star : Icons.star_border,
              semanticLabel: _showingFavorites ? 'Show all stations' : 'Favorites',
            ),
            onPressed: _showFavorites,
          ),
          IconButton(
            icon: const Icon(Icons.add, semanticLabel: 'Add station'),
            onPressed: _showAddStationDialog,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filters
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _showFilterDialog(
                      'Country',
                      [{'name': 'All Countries', 'value': ''}, ..._countries.map((c) => {'name': '${c['name']} (${c['stationcount']})', 'value': c['iso_3166_1'] ?? ''})],
                      _selectedCountryCode,
                      (v) { setState(() => _selectedCountryCode = v); _doSearch(); },
                    ),
                    child: Text(
                      _selectedCountryCode.isEmpty ? 'All Countries' : _countries.firstWhere((c) => c['iso_3166_1'] == _selectedCountryCode, orElse: () => {'name': _selectedCountryCode})['name'] ?? _selectedCountryCode,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _showFilterDialog(
                      'Genre',
                      [{'name': 'All Genres', 'value': ''}, ..._tags.map((t) => {'name': '${t['name']} (${t['stationcount']})', 'value': t['name'] ?? ''})],
                      _selectedTag,
                      (v) { setState(() => _selectedTag = v); _doSearch(); },
                    ),
                    child: Text(
                      _selectedTag.isEmpty ? 'All Genres' : _selectedTag,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search stations...',
                prefixIcon: ExcludeSemantics(child: Icon(Icons.search)),
                isDense: true,
              ),
              onChanged: _onSearchChanged,
            ),
          ),
          const SizedBox(height: 4),
          // Station list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _stations.isEmpty
                    ? Center(
                        child: Text(_errorMessage ?? 'No stations found'))
                    : ListView.builder(
                        itemCount: _stations.length,
                        itemBuilder: (ctx, i) {
                          final station = _stations[i];
                          final isPlaying = _currentStation?.stationuuid ==
                              station.stationuuid;
                          return StationTile(
                            station: station,
                            isPlaying: isPlaying,
                            isFavorite:
                                _favoriteUuids.contains(station.stationuuid),
                            onTap: () => _playStation(station),
                            onFavoriteToggle: () => _toggleFavorite(station),
                          );
                        },
                      ),
          ),
          // Player bar
          if (_currentStation != null)
            StreamBuilder<PlayerState>(
              stream: widget.audioHandler.playerStateStream,
              builder: (ctx, snapshot) {
                final state = snapshot.data;
                final isActive = widget.audioHandler.isPlaying;
                final isPaused = widget.audioHandler.isPaused;
                final buffering = state?.processingState == ProcessingState.loading ||
                    state?.processingState == ProcessingState.buffering;
                final showPause = isActive && !isPaused;
                return Container(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: SafeArea(
                    top: false,
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            _currentStation!.name,
                            style: Theme.of(context).textTheme.titleSmall,
                            overflow: TextOverflow.ellipsis,
                            semanticsLabel: 'Now playing: ${_currentStation!.name}',
                          ),
                        ),
                        if (buffering && !isPaused)
                          const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        else
                          IconButton(
                            icon: Icon(
                              showPause ? Icons.pause_circle_filled : Icons.play_circle_filled,
                              semanticLabel: showPause ? 'Pause' : 'Play',
                            ),
                            iconSize: 40,
                            onPressed: _togglePause,
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
