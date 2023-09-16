#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import func, and_

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venue', lazy=True)

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True)

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.now(), nullable=False)

    def __repr__(self):
       return f'<Show {self.id} {self.start_time}>'
    
#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    areas = db.session.query(Venue.city, Venue.state).distinct(Venue.city, Venue.state)
    data = []

    for area in areas:
        result = Venue.query.filter(Venue.state == area.state, Venue.city == area.city).all()
        venue_data = []

        for venue in result:
            # Filter the shows for each venue to count upcoming shows
            num_upcoming_shows = len(Show.query.filter(
                Show.venue_id == venue.id,
                Show.start_time > datetime.now()
            ).all())

            venue_data.append({
                'id': venue.id,
                'name': venue.name,
                'num_upcoming_shows': num_upcoming_shows
            })

        data.append({
            'city': area.city,
            'state': area.state,
            'venues': venue_data
        })

    return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

  search_term = request.form.get('search_term', '')
  venues = db.session.query(Venue).filter(func.lower(Venue.name).contains(func.lower(search_term))).all()
  response_data = []

  for venue in venues:
    venue_data = {
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": 0,  # Initialize to 0 for now, you can update this later
        }
    response_data.append(venue_data)

  response = {
        "count": len(response_data),
        "data": response_data
    }
  
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue_data = db.session.query(Venue).filter(Venue.id == venue_id).first()

  if venue_data:
      past_shows = db.session.query(
          Show.artist_id,
          Artist.name.label('artist_name'),
          Artist.image_link.label('artist_image_link'),
          func.to_char(Show.start_time, 'YYYY-MM-DD HH24:MI:SS').label('start_time')
      ).join(Artist).filter(
          Show.venue_id == venue_id,
          Show.start_time < datetime.now()  # Filter for past shows
      ).all()

      upcoming_shows = db.session.query(
          Show.artist_id,
          Artist.name.label('artist_name'),
          Artist.image_link.label('artist_image_link'),
          func.to_char(Show.start_time, 'YYYY-MM-DD HH24:MI:SS').label('start_time')
      ).join(Artist).filter(
          Show.venue_id == venue_id,
          Show.start_time >= datetime.now()  # Filter for upcoming shows
      ).all()
      # Create a dictionary in the format of the mock data
      venue_detail = {
          "id": venue_data.id,
          "name": venue_data.name,
          "genres": venue_data.genres.split(','),
          "address": venue_data.address,
          "city": venue_data.city,
          "state": venue_data.state,
          "phone": venue_data.phone,
          "website": venue_data.website,
          "facebook_link": venue_data.facebook_link,
          "seeking_talent": venue_data.seeking_talent,
          "seeking_description": venue_data.seeking_description,
          "image_link": venue_data.image_link,
          "past_shows": past_shows,
          "upcoming_shows": upcoming_shows,
          "past_shows_count": len(past_shows),
          "upcoming_shows_count": len(upcoming_shows),
      }

      return render_template('pages/show_venue.html', venue=venue_detail)
  else:
      # Handle the case where the venue_id is not found in the database
      flash('Venue not found', 'error')
      return redirect(url_for('index'))

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    address = request.form['address']
    genres_list = request.form.getlist('genres')
    facebook_link = request.form['facebook_link']
    image_link = request.form['image_link']
    website_link = request.form['website_link']
    seeking_talent = request.form.get('seeking_talent')
    seeking_description = request.form.get('seeking_description')

    if seeking_talent == "y":
      seeking_talent = True
    else:
      seeking_talent = False

    if not seeking_description:
       seeking_description = None

    genres_str = ', '.join(genres_list)

    venue = Venue(
       name=name, 
       city=city, 
       state=state, 
       address=address, 
       phone=phone, 
       image_link=image_link,
       genres=genres_str,
       facebook_link=facebook_link,
       website=website_link,
       seeking_talent=seeking_talent,
       seeking_description=seeking_description
       )
    
    db.session.add(venue)
    db.session.commit()

    flash('Venue ' + name + ' was successfully listed!')
  except Exception as error:
    db.session.rollback()
    flash('An error occurred. Venue ' + name + ' could not be listed.' + str(error))

  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  try:
    # Find the venue by its ID and delete it
    venue = Venue.query.get(venue_id)
    
    if venue is None:
        return jsonify({'message': 'Venue not found'}), 404
    db.session.delete(venue)
    db.session.commit()
    
    return jsonify({'message': 'Venue deleted successfully'}), 200
  except Exception as error:
    db.session.rollback()
    return jsonify({'message': 'An error occurred while deleting the venue', 'error': str(error)}), 500
  finally:
      db.session.close()

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".

  search_term = request.form.get('search_term', '')

  artists = Artist.query.filter(func.lower(Artist.name).contains(func.lower(search_term))).all()

  response = {
      "count": len(artists),
      "data": []
  }
  for artist in artists:
      num_upcoming_shows = Show.query.filter(
          Show.artist_id == artist.id,
          Show.start_time > datetime.now()
      ).count()
      response["data"].append({
          "id": artist.id,
          "name": artist.name,
          "num_upcoming_shows": num_upcoming_shows
      })

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id

  artist_data = db.session.query(Artist).filter(Artist.id == artist_id).group_by(Artist.id).first()
  if artist_data:
    past_shows = db.session.query(
      Show.venue_id.label('venue_id'),
      Venue.name.label('venue_name'),
      Venue.image_link.label('venue_image_link'),
      func.to_char(Show.start_time, 'YYYY-MM-DD HH24:MI:SS').label('start_time')
    ).join(Venue).filter(
      and_(
          Show.artist_id == artist_id,
          Show.start_time < datetime.now()
      )
    ).all()

    upcoming_shows = db.session.query(
      Show.venue_id.label('venue_id'),
      Venue.name.label('venue_name'),
      Venue.image_link.label('venue_image_link'),
      func.to_char(Show.start_time, 'YYYY-MM-DD HH24:MI:SS').label('start_time')
    ).join(Venue).filter(
      and_(
          Show.artist_id == artist_id,
          Show.start_time >= datetime.now()
    )
    ).all()
    
    artist_detail = {
      "id": artist_data.id,
      "name": artist_data.name,
      "genres": artist_data.genres.split(','),
      "city": artist_data.city,
      "state": artist_data.state,
      "phone": artist_data.phone,
      "website": artist_data.website,
      "facebook_link": artist_data.facebook_link,
      "seeking_venue": artist_data.seeking_venue,
      "seeking_description": artist_data.seeking_description,
      "image_link": artist_data.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=artist_detail)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()

  artist = Artist.query.get(artist_id)

  if not artist:
    # Return a 404 error if the artist doesn't exist
    return abort(404)

  form.name.data = artist.name
  form.genres.data = artist.genres.split(', ')
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.website_link.data = artist.website
  form.facebook_link.data = artist.facebook_link
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description
  form.image_link.data = artist.image_link

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    artist = Artist.query.get(artist_id)

    if not artist:
        # Handle the case where the artist does not exist
        return abort(404)

    artist.name = request.form.get('name')
    artist.genres = ', '.join(request.form.getlist('genres'))  
    artist.city = request.form.get('city')
    artist.state = request.form.get('state')
    artist.phone = request.form.get('phone')
    artist.website = request.form.get('website_link')
    artist.facebook_link = request.form.get('facebook_link')
    artist.seeking_venue = request.form.get('seeking_venue') == 'y'
    artist.seeking_description = request.form.get('seeking_description')
    artist.image_link = request.form.get('image_link')

    db.session.commit()

  except Exception as error:
    db.session.rollback()
    flash('An error occurred. Artist ' + artist.name + ' could not be updated. Error message: ' + str(error), 'error')

  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue={
    "id": 1,
    "name": "The Musical Hop",
    "genres": ["Jazz", "Reggae", "Swing", "Classical", "Folk"],
    "address": "1015 Folsom Street",
    "city": "San Francisco",
    "state": "CA",
    "phone": "123-123-1234",
    "website": "https://www.themusicalhop.com",
    "facebook_link": "https://www.facebook.com/TheMusicalHop",
    "seeking_talent": True,
    "seeking_description": "We are on the lookout for a local artist to play every two weeks. Please call us.",
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60"
  }
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    name = request.form.get('name')
    city = request.form.get('city')
    state = request.form.get('state')
    phone = request.form.get('phone')
    genres_list = request.form.getlist('genres')
    image_link = request.form.get('image_link')
    facebook_link = request.form.get('facebook_link')
    website = request.form.get('website')
    seeking_venue = request.form.get('seeking_venue')
    seeking_description = request.form.get('seeking_description')

    if seeking_venue == "y":
      seeking_venue = True
    else:
      seeking_venue = False

    if not seeking_description:
       seeking_description = None

    genres_str = ', '.join(genres_list)

    # Create a new Artist instance
    artist = Artist(
        name=name,
        city=city,
        state=state,
        phone=phone,
        genres=genres_str,
        image_link=image_link,
        facebook_link=facebook_link,
        website=website,
        seeking_venue=seeking_venue,
        seeking_description=seeking_description
    )

    db.session.add(artist)
    db.session.commit()

    flash('Artist ' + artist.name + ' was successfully listed!')

  except Exception as error:
    db.session.rollback()
    flash('An error occurred. Artist ' + name + ' could not be listed. Error message: ' + str(error), 'error')

  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows

  shows_data = db.session.query(
    Show.venue_id,
    Venue.name.label('venue_name'),
    Show.artist_id,
    Artist.name.label('artist_name'),
    Artist.image_link.label('artist_image_link'),
    Show.start_time
  ).join(Venue).join(Artist).all()

  formatted_shows_data = [
    {
        "venue_id": show.venue_id,
        "venue_name": show.venue_name,
        "artist_id": show.artist_id,
        "artist_name": show.artist_name,
        "artist_image_link": show.artist_image_link,
        "start_time": show.start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    }
    for show in shows_data
  ]

  return render_template('pages/shows.html', shows=formatted_shows_data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    artist_id = request.form.get('artist_id')
    venue_id = request.form.get('venue_id')
    start_time = request.form.get('start_time')

    show = Show(artist_id=artist_id, venue_id=venue_id, start_time=start_time)

    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
        
  except Exception as error:
    db.session.rollback()
    flash('An error occurred. Show could not be listed. Error message: ' + str(error), 'error')
        
  finally:
    db.session.close()
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
