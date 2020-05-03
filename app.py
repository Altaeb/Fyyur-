#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *
from flask_migrate import Migrate
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)
# connect to a local postgresql database
row_to_dict = lambda r: {c.name: getattr(r, c.name) for c in r.__table__.columns}


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format = "EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format = "EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)


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
  # num_shows should be aggregated based on number of upcoming shows per venue.
  # Example of data
  # {
  #     "city": "San Francisco",
  #     "state": "CA",
  #     "venues": [{
  #         "id": 1,
  #         "name": "The Musical Hop",
  #         "num_upcoming_shows": 0,
  #     }, {
  #         "id": 3,
  #         "name": "Park Square Live Music & Coffee",
  #         "num_upcoming_shows": 1,
  #     }]
  # }
  venue_groups = db.session.query(Venue.city, Venue.state).group_by(
      Venue.city, Venue.state).all()
  print(venue_groups)
  result = []
  for venue_group in venue_groups:
      city_name = venue_group[0]
      city_state = venue_group[1]
      q = db.session.query(Venue).filter(
          Venue.city == city_name, Venue.state == city_state)
      group = {
          "city": city_name,
          "state": city_state,
          "venues": []
      }
      venues = q.all()
      for venue in venues:
          print(venue.id)
          group['venues'].append({
              "id": venue.id,
              "name": venue.name,
              "num_upcoming_show": len(venue.shows)
          })
      result.append(group)
  return render_template('pages/venues.html', areas=result)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues = db.session.query(Venue).filter((Venue.name.like('%{}%'.format(search_term))) |
                                            (Venue.city.like('%{}%'.format(search_term))) |
                                            (Venue.state.like('%{}%'.format(search_term)))).all()
    response = {
        "count": 0,
        "data": []
  }
    for venue in venues:
        v_obj = {
            "id": venue.id,
            "name": venue.name,
            "num_upcoming_shows": len(venue.shows)
        }
        response["data"].append(v_obj)
    response['count'] = len(response['data'])
    return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  data1 = {
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
    "image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
    "past_shows": [{
      "artist_id": 4,
      "artist_name": "Guns N Petals",
      "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
      "start_time": "2019-05-21T21:30:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }
  venue = db.session.query(Venue).filter_by(id=venue_id).first()
  if not venue:
      flash('Venue not found')
      redirect('/venues')
  result = row_to_dict(venue)
  result["genres"] = result["genres"].split(';') if result['genres'] else []
  result["past_shows"] = []
  result["upcoming_shows"] = []
  now_datetime = datetime.now()
  for show in venue.shows:
      show_obj = {
          "artist_id": show.artist.id,
          "artist_name": show.artist.name,
          "artist_image_link": show.artist.image_link,
          "start_time": str(show.start_time)
      }
      if show.start_time <= now_datetime:
          result['past_shows'].append(show_obj)
      else:
          result['upcoming_shows'].append(show_obj)
  result['past_shows_count'] = len(result['past_shows'])
  result['upcoming_shows_count'] = len(result['upcoming_shows'])
  return render_template('pages/show_venue.html', venue=result)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    #  insert form data as a new Venue record in the db, instead
    #  modify data to be the data object returned from db insertion
    form = VenueForm()
    if not form.validate_on_submit():
        # on successful db insert, flash success
        data = request.form
        venue = Venue(name=data['name'], address=data['address'], city=data['city'], state=data['state'],
                      phone=data['phone'], image_link=data['image_link'], facebook_link=data['facebook_link'],
                      website=data['website'])
        venue.seeking_talent = True if data['seeking_talent'] == 'true' else False
        venue.seeking_description = data['seeking_description']
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    else:
        flash('Wrong data to create a Venue')
        return render_template('forms/new_venue.html', form=form)
    # TODO: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        flash('No venue to delete')
        return redirect('/venues')
    if len(venue.shows) != 0:
        flash('You can\'t delete venues linked to some shows')
        return redirect('/artists/'+str(venue_id))
    db.session.delete(venue)
    db.session.commit()
    return redirect('/venues')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = db.session.query(Artist).all()
  result = []
  for artist in artists:
      result.append({
          "id": artist.id,
          "name": artist.name
      })
  return render_template('pages/artists.html', artists=result)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists = db.session.query(Artist).filter((Artist.name.like('%{}%'.format(search_term))) |
                                            (Artist.city.like('%{}%'.format(search_term))) |
                                            (Artist.state.like('%{}%'.format(search_term)))).all()
    response = {
        "count": 0,
        "data": []
  }
    for artist in artists:
        v_obj = {
            "id": artist.id,
            "name": artist.name,
            "num_upcoming_shows": len(artist.shows)
        }
        response["data"].append(v_obj)
    response['count'] = len(response['data'])
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  data1 = {
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    "past_shows": [{
      "venue_id": 1,
      "venue_name": "The Musical Hop",
      "venue_image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
      "start_time": "2019-05-21T21:30:00.000Z"
    }],
    "upcoming_shows": [],
    "past_shows_count": 1,
    "upcoming_shows_count": 0,
  }


artist = db.session.query(Artist).filter_by(id=artist_id).first()
if not artist:
    flash('User not found!', 'error')
  return redirect('/artists')
result = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.split(';'),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "facebook_link": artist.facebook_link,
    "website": artist.website,
    "past_shows": [],
    "past_shows_count": 0,
    "upcoming_shows_count": 0,
  }
  #  now_datetime = datetime.now()
for show in artist.shows:
    show_obj = {
        "venue_id": show.venue.id,
        "venue_name": show.venue.name,
        "venue_image_link": show.venue.image_link,
        "start_time": str(show.start_time)
    }
    print(show.start_time)
    if show.start_time <= datetime.now():
        result['past_shows'].append(show_obj)
    else:
        result['upcoming_shows'].append(show_obj)
result['past_shows_count'] = len(result['past_shows'])
result['upcoming_shows_count'] = len(result['upcoming_shows'])
return render_template('pages/show_artist.html', artist=result)

@app.route('/artists/<artist_id>/delete', methods=['GET'])
def delete_artist(artist_id):
    artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
    if not artist:
        flash('No artist to delete')
        return redirect('/artists')
    if len(artist.shows) != 0:
        flash('You can\'t delete artists linked to some shows')
        return redirect('/artists/'+str(artist_id))
    db.session.delete(artist)
    db.session.commit()
    return redirect('/artists')

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist={
    "id": 4,
    "name": "Guns N Petals",
    "genres": ["Rock n Roll"],
    "city": "San Francisco",
    "state": "CA",
    "phone": "326-123-5000",
    "website": "https://www.gunsnpetalsband.com",
    "facebook_link": "https://www.facebook.com/GunsNPetals",
    "seeking_venue": True,
    "seeking_description": "Looking for shows to perform at in the San Francisco Bay Area!",
    "image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"
  }

  artist = db.session.query(Artist).filter_by(id=artist_id).first()
  if not artist:
      flash('User not found!', 'error')
      return redirect('/artists')
  result = {
      "id": artist.id,
      "name": artist.name,
      "genres": artist.genres.split(';'),
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "seeking_venue": artist.seeking_venue,
      "seeking_description": artist.seeking_description,
      "image_link": artist.image_link,
      "facebook_link": artist.facebook_link,
      "website": artist.website,
  }
  return render_template('forms/edit_artist.html', form=form, artist=result)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
  form_data = request.form
  artist.name = form_data['name']
  artist.city = form_data['city']
  artist.state = form_data['state']
  artist.phone = form_data['phone']
  artist.genres = ';'.join(form_data.getlist('genres'))
  artist.image_link = form_data['image_link']
  artist.facebook_link = form_data['facebook_link']
  artist.website = form_data['website']
  artist.seeking_venue = True if form_data['seeking_venue']=='true' else False
  artist.seeking_description = form_data['seeking_description']
  db.session.commit()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  # TODO: populate form with values from venue with ID <venue_id>
    venue = db.session.query(Venue).filter(Venue.id==venue_id).first()
    venue = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres.split(';') if venue.genres else [],
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link
    }
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  form_data = request.form
  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  venue.name = form_data['name']
  venue.city = form_data['city']
  venue.state = form_data['state']
  venue.address = form_data['address']
  venue.phone = form_data['phone']
  venue.genres = ';'.join(form_data.getlist('genres'))
  venue.image_link = form_data['image_link']
  venue.facebook_link = form_data['facebook_link']
  venue.website = form_data['website']
  venue.seeking_talent = True if form_data['seeking_talent'] == 'true' else False
  venue.seeking_description = form_data['seeking_description']
  db.session.commit()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  form_data = request.form
  artist = Artist()
  artist.name = form_data['name']
  artist.city = form_data['city']
  artist.state = form_data['state']
  artist.phone = form_data['phone']
  artist.genres = ';'.join(form_data.getlist('genres'))
  artist.image_link = form_data['image_link']
  artist.facebook_link = form_data['facebook_link']
  artist.website = form_data['website']
  artist.seeking_venue = True if form_data['seeking_venue']=='true' else False
  artist.seeking_description = form_data['seeking_description']
  db.session.add(artist)
  db.session.commit()
  print(form_data['genres'])
  # on successful db insert, flash success
  flash('Artist ' + request.form['name'] + ' was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  data=[{
    "venue_id": 1,
    "venue_name": "The Musical Hop",
    "artist_id": 4,
    "artist_name": "Guns N Petals",
    "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
    "start_time": "2019-05-21T21:30:00.000Z"
  }]
  shows = db.session.query(Show).all()
  result = []
  for show in shows:
      artist = show.artist
      venue = show.venue
      result.append({
          "venue_id": venue.id if venue else None,
          "venue_name": venue.name if venue else None,
          "artist_id": artist.id if artist else None,
          "artist_name": artist.name if artist else None,
          "artist_image_link": artist.image_link if artist else None,
          "start_time": str(show.start_time),
      })
  return render_template('pages/shows.html', shows=result)

@app.route('/shows/search', methods=['POST'])
def search_shows():
    search_term = request.form.get('search_term', '')
    shows = db.session.query(Show).filter((Show.artist.has(Artist.name.like('%{}%'.format(search_term)))) |
                                          (Show.venue.has(Venue.name.like('%{}%'.format(search_term))))).all()
    result = []
    for show in shows:
        artist = show.artist
        venue = show.venue
        result.append({
            "venue_id": venue.id if venue else None,
            "venue_name": venue.name if venue else None,
            "artist_id": artist.id if artist else None,
            "artist_name": artist.name if artist else None,
            "artist_image_link": artist.image_link if artist else None,
            "start_time": str(show.start_time),
        })
    return render_template('pages/search_shows.html', shows=result, count=len(result), search_term=search_term)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  shows = db.session.query(Show).all()
  result = []
  for show in shows:
      artist = show.artist
      venue = show.venue
      result.append({
          "venue_id": venue.id if venue else None,
          "venue_name": venue.name if venue else None,
          "artist_id": artist.id if artist else None,
          "artist_name": artist.name if artist else None,
          "artist_image_link": artist.image_link if artist else None,
          "start_time": str(show.start_time),
      })
  return render_template('pages/shows.html', shows=result)
  flash('Show was successfully listed!')
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
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
