import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import '../models/station.dart';

class StationTile extends StatelessWidget {
  final Station station;
  final bool isPlaying;
  final bool isFavorite;
  final VoidCallback onTap;
  final VoidCallback onFavoriteToggle;

  const StationTile({
    super.key,
    required this.station,
    required this.isPlaying,
    required this.isFavorite,
    required this.onTap,
    required this.onFavoriteToggle,
  });

  @override
  Widget build(BuildContext context) {
    final subtitle = [
      if (station.country.isNotEmpty) station.country,
      if (station.tags.isNotEmpty) station.tags,
    ].join(' - ');

    final favAction = isFavorite ? 'Remove from favorites' : 'Add to favorites';

    return Semantics(
      onTap: onTap,
      onTapHint: 'Play',
      customSemanticsActions: {
        CustomSemanticsAction(label: favAction): onFavoriteToggle,
      },
      child: ListTile(
        leading: Icon(
          isPlaying ? Icons.play_circle_filled : Icons.radio,
          color: isPlaying ? Theme.of(context).colorScheme.primary : null,
          semanticLabel: isPlaying ? 'Playing' : null,
        ),
        title: Text(
          station.name,
          style: isPlaying
              ? TextStyle(
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.primary)
              : null,
        ),
        subtitle: subtitle.isNotEmpty
            ? Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis)
            : null,
        trailing: ExcludeSemantics(
          child: IconButton(
            icon: Icon(isFavorite ? Icons.star : Icons.star_border),
            onPressed: onFavoriteToggle,
          ),
        ),
        onTap: onTap,
      ),
    );
  }
}
