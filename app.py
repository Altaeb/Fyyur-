#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
# import datetime
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

"""Function to convert object retrieved with SQLAlchemy in dictionaries"""
row_to_dict = lambda r: {c.name: getattr(r, c.name) for c in r.__table__.columns}

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format="EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format="EE MM, dd, y h:mma"
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
    """
    Get the list of venues to show to the user
    :return: Template with rendered retrieved venues
    """
    venue_groups = db.session.query(Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
    print(venue_groups)
    result = []
    # Grouping venues by city and state
    for venue_group in venue_groups:
        city_name = venue_group[0]
        city_state = venue_group[1]
        q = db.session.query(Venue).filter(Venue.city == city_name, Venue.state == city_state)
        group = {
            "city": city_name,
            "state": city_state,
            "venues": []
        }
        venues = q.all()
        # Listing venues in the city/state group
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
    """
    Retrieve venues by a search term passed by the user. Filter is applied searching term in venue name, city or state
    :return: Template with rendered retrieved filtered venues
    """
    search_term = request.form.get('search_term', '')
    venues = db.session.query(Venue).filter((Venue.name.ilike('%{}%'.format(search_term))) |
                                            (Venue.city.ilike('%{}%'.format(search_term))) |
                                            (Venue.state.ilike('%{}%'.format(search_term)))).all()
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
    """
    Retrieve data about the specified venue by its ID
    :param venue_id: ID of the venue to show
    :return: Rendered template with desired venue. If the venue doesn't exists it redirect you to venue list with a flash error
    """
    venue = db.session.query(Venue).filter_by(id=venue_id).first()
    if not venue:
        flash('Venue not found')
        redirect('/venues')
    result = row_to_dict(venue)
    result["genres"] = result["genres"].split(';') if result['genres'] else []
    result["past_shows"] = []
    result["upcoming_shows"] = []
    now_datetime = datetime.now()
    # Parse show to count and add show infos linked to the venue
    for show in venue.shows:
        show_obj = {
            "artist_id": show.artist.id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        }
        # Check if the show is already completed or not
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
    """
    Render template to create a venue
    :return: Rendered template to create a venue
    """
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    """
    Create a venue with user input
    :return: If venue is created it redirect you to the home page with a success message. If it fails it redirect you to venue creation form with the error message
    """
    form = VenueForm()
    if not form.validate_on_submit():
        # on successful db insert, flash success
        data = request.form
        venue = Venue(name=data['name'], address=data['address'], city=data['city'], state=data['state'],
                      phone=data['phone'], image_link=data.get('image_link',''), facebook_link=data.get('facebook_link', ''),
                      website=data['website'])
        venue.seeking_talent = True if data['seeking_talent'] == 'true' else False
        venue.seeking_description = data.get('seeking_description', '')
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    else:
        flash('Wrong data to create a Venue')
        return render_template('forms/new_venue.html', form=form)
    # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>/delete', methods=['GET'])
def delete_venue(venue_id):
    """
    Delete the desired venue
    :param venue_id:
    :return: Redirect to venue list with a success message if venue is delete, with a fail message otherwise
    """
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
    """
    Show the list of artist to the user
    :return: Rendered template with the list of artists
    """
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
    """
    Retrieve artists by a search term passed by the user. Filter is applied searching term in artists name, city or state
    :return: Template with rendered retrieved filtered artists
    """
    search_term = request.form.get('search_term', '')
    artists = db.session.query(Artist).filter((Artist.name.ilike('%{}%'.format(search_term))) |
                                            (Artist.city.ilike('%{}%'.format(search_term))) |
                                            (Artist.state.ilike('%{}%'.format(search_term)))).all()
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
    """
    Retrieve data about the specified artist by its ID
    :param artist_id: ID of the artist to show
    :return: Rendered template with desired artist. If the artist doesn't exists it redirects you to artist list with a flash error
    """
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
        "upcoming_shows": [],
        "past_shows_count": 0,
        "upcoming_shows_count": 0
    }
    now_datetime = datetime.now()
    # Parse show to count and add show infos linked to the artist
    for show in artist.shows:
        show_obj = {
            "venue_id": show.venue.id,
            "venue_name": show.venue.name,
            "venue_image_link": show.venue.image_link,
            "start_time": str(show.start_time)
        }
        if show.start_time <= now_datetime:
            result['past_shows'].append(show_obj)
        else:
            result['upcoming_shows'].append(show_obj)
    result['past_shows_count'] = len(result['past_shows'])
    result['upcoming_shows_count'] = len(result['upcoming_shows'])
    return render_template('pages/show_artist.html', artist=result)

@app.route('/artists/<artist_id>/delete', methods=['GET'])
def delete_artist(artist_id):
    """
    Delete the desired artist
    :param artist_id:
    :return: Redirect to artist list with a success message if artist is delete, with a fail message otherwise
    """
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
    """
    Show edit form for the desired artist
    :param artist_id: ID of the artist to edit
    :return: Rendered template with the edit form
    """
    form = ArtistForm()
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
    """
    Edit the artist with input passed through the artist edit page
    :param artist_id: ID of the artist to edit
    :return: Redirect the the edited artist show page
    """
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
    """
    Show edit form for the desired venue
    :param venue_id: ID of the venue to edit
    :return: Rendered template with the edit form
    """
    form = VenueForm()
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
    """
    Edit the venue with input passed through the venue edit page
    :param artist_id: ID of the venue to edit
    :return: Redirect the the edited venue show page
    """
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
    """
    Render template to create an artist
    :return: Rendered template to create an artist
    """
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    """
    Create an artist with user input
    :return: If artist is created it redirects you to the home page with a success message. If it fails it redirect you to artist creation form with the error message
    """
    form_data = request.form
    artist = Artist()
    artist.name = form_data['name']
    artist.city = form_data['city']
    artist.state = form_data['state']
    artist.phone = form_data['phone']
    artist.genres = ';'.join(form_data.getlist('genres'))
    artist.image_link = form_data.get('image_link', '')
    artist.facebook_link = form_data.get('facebook_link', '')
    artist.website = form_data.get('website', '')
    artist.seeking_venue = True if form_data['seeking_venue']=='true' else False
    artist.seeking_description = form_data.get('seeking_description', '')
    db.session.add(artist)
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
    # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    """
    Show the list of all registered shows
    :return: Rendered template to list shows
    """
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
    """
    Search show by a search term. Search term is compared with artist and venue names linked to the shows
    :return: Rendered template of filtered shows
    """
    search_term = request.form.get('search_term', '')
    shows = db.session.query(Show).filter((Show.artist.has(Artist.name.ilike('%{}%'.format(search_term)))) |
                                          (Show.venue.has(Venue.name.ilike('%{}%'.format(search_term))))).all()
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
    """
    Render form to create a show
    :return: Rendered form to create a show
    """
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    """
    Create a show from form to create shows
    :return: Redirection to home with a success message if the show is created. Redirect to show creation form if creation fails
    """
    form_data = request.form
    show = Show()
    artist = db.session.query(Artist).filter_by(id=form_data['artist_id']).first()
    # Check if artist to link exists
    if not artist:
        flash('Wrong user for the show!')
        return redirect('/shows/create')
    venue = db.session.query(Venue).filter_by(id=form_data['venue_id']).first()
    # Check if Venue to link to the show exist
    if not venue:
        flash('Wrong venue for the show!')
        return redirect('/shows/create')
    try:
        show.start_time = dateutil.parser.parse(form_data['start_time'])
    except:
        flash('Wrong date for the show!')
        return redirect('/shows/create')
    show.artist_id = artist.id
    show.venue_id = venue.id
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
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
